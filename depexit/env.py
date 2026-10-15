"""Isolated execution environments for the target repository.

Every function here runs real processes (venv creation, pip/uv installs,
imports, pytest) and returns what it observed, so its results are tagged
as measured evidence in the capsule.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from pathlib import Path

IS_WIN = sys.platform.startswith("win")

PROBE = r'''
import json, sys
from importlib import metadata
top = {}
for mod, dists in metadata.packages_distributions().items():
    for d in dists:
        top.setdefault(d, set()).add(mod)
out = {}
for dist in metadata.distributions():
    name = dist.metadata["Name"]
    if not name:
        continue
    scripts = [ep.name for ep in dist.entry_points if ep.group == "console_scripts"]
    out[name] = {
        "version": dist.version,
        "modules": sorted(m for m in top.get(name, ()) if not m.startswith("_")),
        "console_scripts": scripts,
        "requires": dist.requires or [],
    }
print(json.dumps({"python": sys.version.split()[0], "dists": out}))
'''


@dataclass
class CmdResult:
    cmd: list[str]
    code: int
    seconds: float
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.code == 0

    def tail(self, n: int = 40) -> str:
        text = (self.stdout + "\n" + self.stderr).strip().splitlines()
        return "\n".join(text[-n:])


def run(cmd, cwd=None, env=None, timeout=900) -> CmdResult:
    start = time.monotonic()
    try:
        p = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8", errors="replace")
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        code, out, err = 124, e.stdout or "", (e.stderr or "") + f"\n[depexit] timed out after {timeout}s"
    except FileNotFoundError as e:
        code, out, err = 127, "", str(e)
    return CmdResult([str(c) for c in cmd], code, round(time.monotonic() - start, 2), out, err)


@dataclass
class Env:
    path: Path
    python_cmd: str
    installer: str
    log: list[dict] = field(default_factory=list)

    @property
    def python(self) -> Path:
        return self.path / ("Scripts/python.exe" if IS_WIN else "bin/python")

    def record(self, step: str, r: CmdResult) -> CmdResult:
        self.log.append({"step": step, "cmd": " ".join(r.cmd), "exit_code": r.code,
                         "seconds": r.seconds, "output_tail": r.tail(25)})
        return r


def pick_installer(pref: str) -> str:
    if pref == "auto":
        return "uv" if shutil.which("uv") else "pip"
    return pref


def create(path: Path, python_cmd: str, installer: str) -> tuple[Env, CmdResult]:
    if path.exists():
        shutil.rmtree(path)
    env = Env(path, python_cmd, installer)
    if installer == "uv":
        r = run(["uv", "venv", "--quiet", "--seed", "--python", python_cmd, path])
    else:
        r = run([python_cmd, "-m", "venv", path])
    return env, env.record("create-venv", r)


def install(env: Env, args: list[str], cwd: Path, step: str) -> CmdResult:
    if env.installer == "uv":
        cmd = ["uv", "pip", "install", "--python", env.python, *args]
    else:
        cmd = [env.python, "-m", "pip", "install", "--disable-pip-version-check", "-q", *args]
    return env.record(step, run(cmd, cwd=cwd))


def pip_check(env: Env) -> CmdResult:
    if env.installer == "uv":
        return env.record("pip-check", run(["uv", "pip", "check", "--python", env.python]))
    return env.record("pip-check", run([env.python, "-m", "pip", "check"]))


def inventory(env: Env) -> dict:
    r = env.record("inventory", run([env.python, "-c", PROBE]))
    if not r.ok:
        return {"python": None, "dists": {}, "error": r.tail()}
    return json.loads(r.stdout)


_WARN_RE = re.compile(r"(?P<file>[^\s:]+\.py):(?P<line>\d+): (?P<cat>\w*Warning): (?P<msg>.+)")


def import_probe(env: Env, module: str, cwd: Path) -> dict:
    """Import a module on its own, recording failure and import-time warnings."""
    r = run([env.python, "-W", "always", "-c", f"import {module}"], cwd=cwd, timeout=120)
    warnings = [m.groupdict() for m in _WARN_RE.finditer(r.stderr)]
    err = ""
    if not r.ok:
        lines = [l for l in r.stderr.strip().splitlines() if l.strip()]
        err = lines[-1] if lines else f"exit {r.code}"
    return {"module": module, "ok": r.ok, "error": err,
            "traceback_tail": r.tail(12) if not r.ok else "", "warnings": warnings}


@dataclass
class TestCase:
    id: str
    outcome: str      # passed | failed | error | skipped
    message: str = ""
    detail: str = ""
    seconds: float = 0.0


@dataclass
class TestRun:
    label: str
    exit_code: int
    seconds: float
    cases: list[TestCase]
    warnings: list[dict]
    collection_error: str = ""
    output_tail: str = ""

    def counts(self) -> dict:
        c = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
        for t in self.cases:
            c[t.outcome] = c.get(t.outcome, 0) + 1
        return c

    def outcome_map(self) -> dict:
        return {t.id: t.outcome for t in self.cases}

    def to_dict(self) -> dict:
        d = asdict(self)
        d["counts"] = self.counts()
        return d


def _parse_junit(path: Path) -> list[TestCase]:
    if not path.exists():
        return []
    root = ET.parse(path).getroot()
    out = []
    for tc in root.iter("testcase"):
        cls, name = tc.get("classname", ""), tc.get("name", "")
        tid = f"{cls.replace('.', '/')}.py::{name}" if cls else name
        outcome, msg, detail = "passed", "", ""
        for tag in ("failure", "error", "skipped"):
            el = tc.find(tag)
            if el is not None:
                outcome = {"failure": "failed"}.get(tag, tag)
                msg = el.get("message", "") or ""
                detail = (el.text or "")[-4000:]
                break
        out.append(TestCase(tid, outcome, msg, detail, float(tc.get("time", 0) or 0)))
    return out


def _parse_warning_summary(text: str) -> list[dict]:
    m = re.search(r"=+ warnings summary =+\n(.*?)(?:\n-- Docs:|\n=+)", text, re.S)
    if not m:
        return []
    found, seen = [], set()
    for w in _WARN_RE.finditer(m.group(1)):
        d = w.groupdict()
        d["file"] = re.sub(r"^.*?site-packages[/\\]", "site-packages/", d["file"])
        key = (d["file"], d["line"], d["cat"])
        if key not in seen:
            seen.add(key)
            found.append(d)
    return found


def pytest(env: Env, repo: Path, label: str, junit: Path, targets: list[str] | None = None,
           timeout: int = 900) -> TestRun:
    junit.parent.mkdir(parents=True, exist_ok=True)
    if junit.exists():
        junit.unlink()
    e = dict(os.environ)
    e["PYTHONPATH"] = str(repo) + os.pathsep + e.get("PYTHONPATH", "")
    e.pop("PYTHONWARNINGS", None)
    cmd = [env.python, "-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider",
           "-W", "default", f"--junitxml={junit}", *(targets or [])]
    r = env.record(f"pytest:{label}", run(cmd, cwd=repo, env=e, timeout=timeout))
    text = r.stdout + "\n" + r.stderr
    cases = _parse_junit(junit)
    coll = ""
    if r.code in (2, 3, 4) or (not cases and r.code != 5):
        coll = r.tail(30)
    return TestRun(label, r.code, r.seconds, cases, _parse_warning_summary(text), coll, r.tail(30))


_SITE_RE = re.compile(r"site-packages[/\\]([A-Za-z0-9_]+)")
_FROM_RE = re.compile(r"(?:from|module) '([A-Za-z0-9_\.]+)'")
_NAMED_RE = re.compile(r"No module named '([A-Za-z0-9_\.]+)'")


def modules_in_traceback(text: str) -> list[str]:
    """Third-party modules responsible for a failure.

    Frames that merely pass the call through (e.g. a CLI framework) are not
    blamed: only the innermost site-packages frame and any module named in
    the exception message itself are returned.
    """
    mods = []
    frames = [m.group(1) for m in _SITE_RE.finditer(text)]
    if frames:
        mods.append(frames[-1])
    for rx in (_FROM_RE, _NAMED_RE):
        for m in rx.finditer(text):
            top = m.group(1).split(".")[0]
            if top not in mods:
                mods.append(top)
    return mods
