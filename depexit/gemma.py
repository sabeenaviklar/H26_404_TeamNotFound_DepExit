"""Gemma 4 client and prompts.

Two access methods, both free:
  * google : Gemini API (Google AI Studio key) hosting Gemma 4 open weights
  * ollama : a local Ollama server running a Gemma 4 build

The model only ever receives evidence that DepExit observed or measured,
and its answer is treated as an unverified proposal until execution
confirms it.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .net import ssl_context

DEFAULT_MODEL = {"google": "gemma-4-31b-it", "ollama": "gemma4"}
FALLBACKS = {"gemma-4-31b-it": ["gemma-4-26b-a4b-it"], "gemma-4-26b-a4b-it": ["gemma-4-31b-it"]}


def _api_reason(msg: str) -> str:
    """Pull Google's status and message out of an error body for a readable log line."""
    code = re.search(r"HTTP (\d+)", msg)
    status = re.search(r'"status":\s*"([A-Z_]+)"', msg)
    text = re.search(r'"message":\s*"([^"]{0,220})', msg)
    parts = [p for p in (code and f"HTTP {code.group(1)}", status and status.group(1),
                         text and text.group(1)) if p]
    return " ".join(parts) or msg[:240]

SYSTEM = """You are a careful Python dependency-migration engineer working inside an automated tool.
The tool has already inspected and executed the repository. You receive its evidence and must propose
a migration plan that the tool will apply and then verify by running the repository's tests.

Rules:
- Base every claim on the evidence given. If something is not in the evidence, say it is an assumption.
- Prefer, in order: the Python standard library, a maintained drop-in replacement, upgrading the same package,
  removing an unused dependency. Pick the smallest change that removes the risk.
- The target Python version is given. Never propose packages or APIs that do not support it.
- code_edits are exact search-and-replace operations. Each "find" MUST be copied character-for-character
  from the file contents shown (same indentation), and must be unique in that file. Keep edits minimal.
- Do not edit or delete existing tests unless the dependency being removed is the test runner itself.
- requirement_changes edit every manifest that declares the dependency (the tool applies them to all of them).
- suggested_tests are small, self-contained pytest functions (with their imports) that check that the
  behaviour this repository relies on still works after the migration. They must not use the network.
  You may use the fixtures shown in the conftest.py contents if provided.
- Reply with ONE JSON object and nothing else. No markdown fences."""

SCHEMA = """{
  "decision": "replace | upgrade | remove | pin | keep",
  "replacement": {"package": "<pypi name or null>", "version_spec": "<e.g. >=3.1 or empty>", "stdlib_module": "<module or null>"},
  "rationale": "<why, citing the evidence ids such as IMPORT_FAILS or STALE_UPSTREAM>",
  "migration_steps": ["<step>", "..."],
  "requirement_changes": [
    {"action": "remove", "package": "<name>"},
    {"action": "set", "package": "<name>", "requirement": "<name><spec>"},
    {"action": "add", "requirement": "<name><spec>"}
  ],
  "code_edits": [{"file": "<relative path>", "find": "<exact text>", "replace": "<new text>", "why": "<short>"}],
  "suggested_tests": [{"name": "test_<name>", "purpose": "<what it protects>", "code": "<pytest source>"}],
  "compatibility_notes": ["<behaviour differences to watch>"],
  "risks": ["<what could still go wrong>"],
  "confidence": 0.0
}"""


class GemmaError(RuntimeError):
    pass


@dataclass
class Exchange:
    """One prompt/response pair, kept verbatim as evidence."""
    prompt: str
    raw_response: str
    parsed: dict | None
    model: str
    backend: str
    seconds: float
    error: str = ""
    usage: dict = field(default_factory=dict)


class Gemma:
    def __init__(self, backend: str, model: str | None = None, temperature: float = 0.2,
                 ollama_url: str = "http://localhost:11434", timeout: int = 300):
        self.backend = backend
        self.model = model or DEFAULT_MODEL.get(backend, "")
        self.temperature = temperature
        self.ollama_url = ollama_url.rstrip("/")
        self.timeout = timeout
        if backend == "google":
            self.key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not self.key:
                raise GemmaError("Set GEMINI_API_KEY (free key from https://aistudio.google.com/apikey)")

    @property
    def label(self) -> str:
        return f"{self.model} via {self.backend}"

    # -- transport -------------------------------------------------------
    def _post(self, url: str, body: dict, headers: dict) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context()) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            raise GemmaError(f"HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise GemmaError(f"cannot reach {self.backend}: {e}") from None

    def _complete(self, prompt: str) -> tuple[str, dict]:
        if self.backend == "google":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            body = {
                "systemInstruction": {"parts": [{"text": SYSTEM}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": self.temperature, "maxOutputTokens": 16384},
            }
            if getattr(self, "inline_system", False):
                body.pop("systemInstruction")
                body["contents"][0]["parts"][0]["text"] = SYSTEM + "\n\n" + prompt
            data = self._google_with_fallback(body)
            cands = data.get("candidates") or []
            if not cands:
                raise GemmaError(f"no candidates returned: {json.dumps(data)[:400]}")
            finish = cands[0].get("finishReason", "")
            parts = cands[0].get("content", {}).get("parts", [])
            # Gemma 4 may return a separate reasoning part flagged as thought; keep the answer parts
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            usage = dict(data.get("usageMetadata", {}), finishReason=finish)
            if finish and finish != "STOP":
                print(f"[depexit] {self.model}: reply ended with finishReason={finish} ({len(text)} chars)", flush=True)
            return text, usage
        if self.backend == "ollama":
            body = {"model": self.model, "stream": False, "format": "json",
                    "options": {"temperature": self.temperature, "num_ctx": 16384},
                    "messages": [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": prompt}]}
            data = self._post(f"{self.ollama_url}/api/chat", body, {})
            return data.get("message", {}).get("content", ""), {
                "prompt_tokens": data.get("prompt_eval_count"), "output_tokens": data.get("eval_count")}
        raise GemmaError(f"unknown backend {self.backend}")

    def _google_once(self, model: str, body: dict) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        waits = [5, 15, 30]
        for attempt in range(len(waits) + 1):
            try:
                return self._post(url, body, {"x-goog-api-key": self.key})
            except GemmaError as e:
                msg = str(e)
                bad_request_for_system = "HTTP 400" in msg and "instruction" in msg.lower()
                if (bad_request_for_system or ("HTTP 500" in msg and attempt == 0)) and "systemInstruction" in body:
                    # some hosted Gemma versions reject system instructions: fold them into the prompt
                    sys_text = body.pop("systemInstruction")["parts"][0]["text"]
                    first = body["contents"][0]["parts"][0]
                    first["text"] = sys_text + "\n\n" + first["text"]
                    print(f"[depexit] {model}: {_api_reason(msg)} -> resending with the system prompt inline", flush=True)
                    self.inline_system = True
                    continue
                transient = any(c in msg for c in ("HTTP 429", "HTTP 500", "HTTP 503", "HTTP 504"))
                hard_quota = "HTTP 429" in msg and ("limit: 0" in msg or "PerDay" in msg or "per day" in msg.lower())
                reason = _api_reason(msg)
                if not transient or hard_quota or attempt == len(waits):
                    raise GemmaError(f"{model}: {reason}") from None
                print(f"[depexit] {model}: {reason} -> retrying in {waits[attempt]}s", flush=True)
                time.sleep(waits[attempt])
        raise GemmaError(f"{model}: unavailable")

    def _google_with_fallback(self, body: dict) -> dict:
        """Try the chosen Gemma 4 model, then the other Gemma 4 size if it is rate-limited."""
        order = [self.model] + [m for m in FALLBACKS.get(self.model, []) if m != self.model]
        errors = []
        for model in order:
            try:
                data = self._google_once(model, body)
                if model != self.model:
                    print(f"[depexit] switched to {model} for the rest of the run", flush=True)
                    self.model = model
                return data
            except GemmaError as e:
                errors.append(str(e))
                if not any(c in str(e) for c in ("429", "500", "503", "504", "RESOURCE_EXHAUSTED", "UNAVAILABLE")):
                    break
        raise GemmaError(" | ".join(errors))

    # -- public ----------------------------------------------------------
    def ask_json(self, prompt: str) -> Exchange:
        start = time.monotonic()
        raw, usage = self._complete(prompt)
        parsed = extract_json(raw)
        if parsed is None:
            retry = prompt + "\n\nYour previous reply was not valid JSON. Reply again with ONLY the JSON object."
            raw2, usage = self._complete(retry)
            parsed = extract_json(raw2)
            raw = raw + "\n\n--- retry ---\n" + raw2
        return Exchange(prompt, raw, parsed, self.model, self.backend,
                        round(time.monotonic() - start, 1),
                        "" if parsed is not None else "model did not return parseable JSON", usage)


def extract_json(text: str) -> dict | None:
    """Return the first complete TOP-LEVEL JSON object in a model reply.

    A reply cut off mid-object must yield None (so the caller retries), never a
    nested object from inside it: that once turned a truncated plan into a bogus one.
    """
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.M)
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else None
    except json.JSONDecodeError:
        pass
    i, n = 0, len(text)
    while True:
        start = text.find("{", i)
        if start == -1:
            return None
        depth, in_str, esc, end = 0, False, False, None
        for j in range(start, n):
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end is None:
            return None            # unbalanced: the reply was truncated
        try:
            v = json.loads(text[start:end + 1])
            if isinstance(v, dict):
                return v
        except json.JSONDecodeError:
            pass
        i = end + 1                # skip past this object, never into it


REQUIRED_PLAN_KEYS = ("decision", "rationale", "requirement_changes", "code_edits")
DECISIONS = ("replace", "upgrade", "remove", "pin", "keep")


def plan_problems(plan: dict) -> list[str]:
    """Deterministic shape check on a model plan before anything is applied."""
    probs = [f"missing field '{k}'" for k in REQUIRED_PLAN_KEYS if k not in plan]
    if plan.get("decision") not in DECISIONS:
        probs.append(f"decision must be one of {', '.join(DECISIONS)} (got {plan.get('decision')!r})")
    for k in ("requirement_changes", "code_edits", "suggested_tests"):
        if k in plan and not isinstance(plan[k], list):
            probs.append(f"'{k}' must be a list")
    if plan.get("decision") != "keep" and not plan.get("requirement_changes") and not plan.get("code_edits"):
        probs.append("plan changes nothing: no requirement_changes and no code_edits")
    return probs


def plan_prompt(ctx: dict) -> str:
    return (
        "Propose a migration plan for ONE dependency of this repository.\n\n"
        f"## Target\nPython {ctx['python']} (repository supports: {ctx['requires_python'] or 'unspecified'})\n\n"
        f"## Dependency under review\n{json.dumps(ctx['dependency'], indent=2)}\n\n"
        f"## Risk indicators (observed or measured by the tool, not by you)\n{ctx['indicators']}\n\n"
        f"## Where it is used (AST scan + build files)\n{ctx['usages']}\n\n"
        f"## Baseline test run on the target Python\n{ctx['tests']}\n\n"
        f"## Files you may edit (full contents)\n{ctx['files']}\n\n"
        f"## Reply with this JSON shape\n{SCHEMA}\n"
    )


def repair_prompt(original_prompt: str, previous: dict, feedback: str) -> str:
    return (
        original_prompt
        + "\n\n## Your previous plan\n" + json.dumps(previous, indent=2)
        + "\n\n## What happened when the tool applied and executed it\n" + feedback
        + "\n\nReturn a corrected, complete plan (same JSON shape). Fix the cause shown above; "
          "keep the parts that worked."
    )
