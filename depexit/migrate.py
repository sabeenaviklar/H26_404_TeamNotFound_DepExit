"""Phase 2: ask Gemma for a migration plan, apply it to a copy, and verify it.

The plan is untrusted until it has been applied to an isolated copy of the
repository, installed in a fresh environment, and checked against the
baseline: the repository's own tests, import probes, warnings, and the
tests Gemma itself proposed (run against both the original and the
replacement).
"""
from __future__ import annotations

import difflib
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import env as envmod
from . import pypi
from .analyze import Baseline, DepProfile, _attribute_warning
from .gemma import Gemma, GemmaError, plan_prompt, repair_prompt
from .manifest import normalize, parse_requirement
from .scan import SKIP_DIRS, scan, text_references

MAX_FILE_LINES = 400


# --------------------------------------------------------------------- context
def build_context(b: Baseline, p: DepProfile) -> dict:
    files = {u["file"] for u in p.usages}
    files |= {d["file"] for d in p.declared}
    if any(u["kind"] != "text" for u in p.usages) or p.relation != "direct":
        files |= set(b.requirement_files)
        if (b.repo / "pyproject.toml").exists():
            files.add("pyproject.toml")
    conftest = b.repo / "tests" / "conftest.py"
    if conftest.exists():
        files.add("tests/conftest.py")
    blocks = []
    for f in sorted(files):
        path = b.repo / f
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        body = "\n".join(lines[:MAX_FILE_LINES])
        if len(lines) > MAX_FILE_LINES:
            body += f"\n... ({len(lines) - MAX_FILE_LINES} more lines not shown)"
        blocks.append(f"### {f}\n```\n{body}\n```")

    usage_lines = [f"- {u['file']}:{u['line']} [{u['kind']}] {u['symbol']} :: {u['code']}"
                   for u in p.usages] or ["- (no usages found)"]
    ind = [f"- {i.id} ({i.severity}, {i.source}): {i.title}. Evidence: {i.evidence}" for i in p.indicators]
    t = b.tests
    test_txt = "not run"
    if t:
        c = t.counts()
        test_txt = f"{c['passed']} passed, {c['failed']} failed, {c['error']} errors."
        bad = [x for x in t.cases if x.outcome in ("failed", "error")]
        for x in bad[:5]:
            test_txt += f"\n- {x.id}: {x.message[:300]}"
    dep = {
        "name": p.name, "relation": p.relation, "installed_version": p.installed_version,
        "declared": [{k: d[k] for k in ("file", "line", "spec", "group")} for d in p.declared],
        "import_names": p.modules, "console_scripts": p.console_scripts,
        "latest_version_on_pypi": p.registry.get("latest_version"),
        "latest_release_date": p.registry.get("latest_release_date"),
        "upstream_repo_archived": p.registry.get("repo_archived"),
        "import_probe_results": [{k: v for k, v in pr.items() if k != "traceback_tail"} for pr in p.import_probes],
    }
    return {
        "python": b.inventory.get("python"), "requires_python": b.manifest.requires_python,
        "dependency": dep, "indicators": "\n".join(ind), "usages": "\n".join(usage_lines),
        "tests": test_txt, "files": "\n\n".join(blocks),
    }


# ------------------------------------------------------------------- applying
def copy_repo(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*SKIP_DIRS))


def _safe_path(root: Path, rel: str) -> Path | None:
    p = (root / rel).resolve()
    return p if str(p).startswith(str(root.resolve())) else None


def _fuzzy_replace(text: str, find: str, repl: str) -> str | None:
    """Fallback when whitespace differs: match line by line ignoring indentation."""
    want = [l.strip() for l in find.strip("\n").splitlines()]
    lines = text.splitlines(keepends=True)
    hits = []
    for i in range(len(lines) - len(want) + 1):
        if all(lines[i + j].strip() == want[j] for j in range(len(want))):
            hits.append(i)
    if len(hits) != 1:
        return None
    i = hits[0]
    indent = re.match(r"\s*", lines[i]).group(0)
    new = repl.strip("\n").splitlines()
    base = len(re.match(r"\s*", new[0]).group(0)) if new else 0
    new = [indent + l[base:] if l.strip() else "" for l in new]
    tail = "\n" if lines[i + len(want) - 1].endswith("\n") else ""
    return "".join(lines[:i]) + "\n".join(new) + tail + "".join(lines[i + len(want):])


def apply_code_edits(root: Path, edits: list[dict]) -> list[dict]:
    out = []
    for e in edits or []:
        rec = {"file": e.get("file"), "why": e.get("why", ""), "applied": False, "reason": ""}
        path = _safe_path(root, e.get("file", ""))
        find, repl = e.get("find", ""), e.get("replace", "")
        if not path:
            rec["reason"] = "path outside repository"
        elif not path.exists() and not find:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(repl, encoding="utf-8")
            rec.update(applied=True, reason="created new file")
        elif not path.exists():
            rec["reason"] = "file does not exist"
        elif not find:
            rec["reason"] = "empty find string"
        else:
            text = path.read_text(encoding="utf-8")
            n = text.count(find)
            if n == 1:
                path.write_text(text.replace(find, repl, 1), encoding="utf-8")
                rec.update(applied=True, reason="exact match")
            elif n > 1:
                rec["reason"] = f"find text matches {n} places (ambiguous)"
            else:
                new = _fuzzy_replace(text, find, repl)
                if new is not None:
                    path.write_text(new, encoding="utf-8")
                    rec.update(applied=True, reason="matched ignoring indentation")
                else:
                    rec["reason"] = "find text not present in file (model did not copy it exactly)"
        out.append(rec)
    return out


def _req_name(text: str) -> str | None:
    parsed = parse_requirement(text)
    return normalize(parsed[0]) if parsed else None


def apply_requirement_changes(root: Path, changes: list[dict], p: DepProfile,
                              req_files: list[str]) -> list[dict]:
    """Edit requirements*.txt and pyproject.toml text in place, preserving formatting."""
    log = []
    declared_files = {d["file"] for d in p.declared}
    group = p.declared[0]["group"] if p.declared else "runtime"
    targets_for_add = sorted(declared_files) or [
        f for f in req_files if ("dev" in f or "test" in f) == (group == "dev")]
    if not p.declared and (root / "pyproject.toml").exists() and group == "runtime":
        targets_for_add.append("pyproject.toml")
    all_files = sorted(set(req_files) | ({"pyproject.toml"} if (root / "pyproject.toml").exists() else set()))

    for ch in changes or []:
        action = ch.get("action")
        pkg = normalize(ch.get("package") or "") if ch.get("package") else None
        req = (ch.get("requirement") or "").strip()
        if action in ("set", "add") and req and not pkg:
            pkg = _req_name(req)
        touched = []
        for f in all_files:
            path = root / f
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            is_pp = f.endswith(".toml")
            lines = text.splitlines(keepends=True)
            new_lines, hit = [], False
            for line in lines:
                body = line.strip().strip(",").strip('"').strip("'") if is_pp else line.strip()
                if is_pp and not re.match(r'^\s*["\']', line):
                    new_lines.append(line); continue
                name = _req_name(body) if body and not body.startswith("#") else None
                if name and name == pkg and action in ("remove", "set", "add"):
                    hit = True
                    if action == "remove":
                        continue
                    if is_pp:
                        indent = re.match(r"\s*", line).group(0)
                        line = f'{indent}"{req}",\n'
                    else:
                        line = req + "\n"
                new_lines.append(line)
            if action == "add" and not hit and f in targets_for_add:
                if is_pp:
                    joined = "".join(new_lines)
                    m = re.search(r"(dependencies\s*=\s*\[[^\]]*?)(\n\])", joined, re.S)
                    if m:
                        joined = joined[:m.end(1)] + f'\n    "{req}",' + joined[m.end(1):]
                        new_lines, hit = [joined], True
                else:
                    if new_lines and not new_lines[-1].endswith("\n"):
                        new_lines[-1] += "\n"
                    new_lines.append(req + "\n")
                    hit = True
            if hit:
                path.write_text("".join(new_lines), encoding="utf-8")
                touched.append(f)
        log.append({"change": ch, "files": touched, "applied": bool(touched)})
    return log


def unified_diff(a_root: Path, b_root: Path) -> str:
    chunks = []
    names = set()
    for root in (a_root, b_root):
        for p in root.rglob("*"):
            rel = p.relative_to(root)
            if p.is_file() and not any(part in SKIP_DIRS for part in rel.parts):
                names.add(str(rel))
    for rel in sorted(names):
        a, b = a_root / rel, b_root / rel
        try:
            at = a.read_text(encoding="utf-8").splitlines(keepends=True) if a.exists() else []
            bt = b.read_text(encoding="utf-8").splitlines(keepends=True) if b.exists() else []
        except UnicodeDecodeError:
            continue
        if at != bt:
            chunks.extend(difflib.unified_diff(at, bt, f"a/{rel}", f"b/{rel}"))
    return "".join(chunks)


# ------------------------------------------------------------------ verifying
@dataclass
class Attempt:
    number: int
    exchange: dict
    plan: dict | None
    plan_checks: list[dict] = field(default_factory=list)
    edits: list[dict] = field(default_factory=list)
    requirement_log: list[dict] = field(default_factory=list)
    install: dict = field(default_factory=dict)
    candidate_versions: dict = field(default_factory=dict)
    import_probes: list[dict] = field(default_factory=list)
    residual_usages: list[dict] = field(default_factory=list)
    tests: dict | None = None
    comparison: dict = field(default_factory=dict)
    ai_tests: dict = field(default_factory=dict)
    verdict: str = "not-executed"
    verdict_reasons: list[str] = field(default_factory=list)
    diff: str = ""


def _check_plan(plan: dict, cache: Path) -> list[dict]:
    """Deterministic sanity checks on what the model proposed (hallucination guard)."""
    checks = []
    names = set()
    rep = (plan.get("replacement") or {})
    if rep.get("package"):
        names.add(rep["package"])
    for ch in plan.get("requirement_changes") or []:
        if ch.get("action") in ("add", "set") and ch.get("requirement"):
            n = parse_requirement(ch["requirement"])
            if n:
                names.add(n[0])
    for n in sorted(names):
        ok, latest = pypi.exists(n, cache)
        checks.append({"check": f"package '{n}' exists on PyPI", "passed": ok,
                       "detail": f"latest {latest}" if ok else "not found: possible hallucination"})
    sm = rep.get("stdlib_module")
    if sm:
        import sys
        ok = sm.split(".")[0] in sys.stdlib_module_names
        checks.append({"check": f"'{sm}' is a standard-library module", "passed": ok, "detail": ""})
    return checks


def _feedback(a: Attempt) -> str:
    parts = []
    bad = [e for e in a.edits if not e["applied"]]
    if bad:
        parts.append("Edits that could not be applied:\n" + "\n".join(
            f"- {e['file']}: {e['reason']}" for e in bad))
    if a.install and not a.install.get("ok"):
        parts.append("Install failed:\n" + a.install.get("output", ""))
    cmp = a.comparison
    for tid, msg in (cmp.get("regressions") or {}).items():
        parts.append(f"Regression {tid}: {msg}")
    for tid, msg in (cmp.get("still_failing") or {}).items():
        parts.append(f"Still failing {tid}: {msg}")
    if cmp.get("remaining_warnings"):
        parts.append("Warnings still attributed to this dependency:\n" + "\n".join(
            f"- {w['file']}:{w['line']} {w['cat']}: {w['msg'][:200]}" for w in cmp["remaining_warnings"]))
    for pr in a.import_probes:
        if not pr["ok"]:
            parts.append(f"import {pr['module']} failed: {pr['error']}")
    if a.residual_usages:
        parts.append("Old package still referenced at:\n" + "\n".join(
            f"- {u['file']}:{u['line']} {u['code']}" for u in a.residual_usages))
    ai = a.ai_tests.get("candidate") or {}
    for c in ai.get("cases", []):
        if c["outcome"] != "passed":
            parts.append(f"Your suggested test {c['id']} {c['outcome']} on the candidate: {c['message'][:300]}")
    return "\n\n".join(parts) or "No problems observed."


def _write_ai_tests(root: Path, key: str, tests: list[dict]) -> str | None:
    code = [t.get("code", "") for t in tests or [] if "def test" in (t.get("code") or "")]
    if not code:
        return None
    rel = f"tests/test_depexit_{re.sub(r'[^a-z0-9]', '_', key)}.py"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "# Generated by Gemma via DepExit: AI-written characterisation tests.\n"
    path.write_text(header + "\n\n".join(code) + "\n", encoding="utf-8")
    return rel


def _install_candidate(e: envmod.Env, root: Path, req_files: list[str]) -> envmod.CmdResult:
    existing = [f for f in req_files if (root / f).exists()]
    if existing:
        args = []
        for f in existing:
            args += ["-r", f]
        return envmod.install(e, args, root, "install:candidate")
    return envmod.install(e, [".", "pytest"], root, "install:candidate")


def _warnings_for(run: envmod.TestRun, p: DepProfile, mod_to_dist: dict, usages, root: Path) -> list[dict]:
    out = []
    for w in run.warnings:
        d = _attribute_warning(dict(w), mod_to_dist, usages, root)
        if d and normalize(d) == p.key:
            out.append(w)
    return out


def verify(b: Baseline, p: DepProfile, plan: dict, work: Path, python_cmd: str, installer: str,
           a: Attempt, log) -> Attempt:
    root = work / "repo"
    copy_repo(b.repo, root)
    a.edits = apply_code_edits(root, plan.get("code_edits"))
    a.requirement_log = apply_requirement_changes(root, plan.get("requirement_changes"), p, b.requirement_files)
    ai_rel = _write_ai_tests(root, p.key, plan.get("suggested_tests"))
    a.diff = unified_diff(b.repo, root)

    e, r = envmod.create(work / "venv", python_cmd, installer)
    r = _install_candidate(e, root, b.requirement_files)
    pc = envmod.pip_check(e)
    a.install = {"ok": r.ok, "seconds": r.seconds, "output": r.tail(25), "pip_check_ok": pc.ok,
                 "pip_check": pc.tail(10)}
    if not r.ok:
        a.verdict, a.verdict_reasons = "failed", ["candidate dependencies failed to install"]
        return a
    inv = envmod.inventory(e)
    dists = inv.get("dists", {})
    a.candidate_versions = {k: v["version"] for k, v in dists.items()}
    mod_to_dist = {m: d for d, v in dists.items() for m in v["modules"]}
    for d, v in b.inventory.get("dists", {}).items():
        for m in v["modules"]:
            mod_to_dist.setdefault(m, d)

    # import probes: new package modules, and the old ones if still installed
    rep = plan.get("replacement") or {}
    probe_mods = set()
    if rep.get("package"):
        info = next((v for k, v in dists.items() if normalize(k) == normalize(rep["package"])), None)
        probe_mods |= set((info or {}).get("modules", [])[:3])
    if rep.get("stdlib_module"):
        probe_mods.add(rep["stdlib_module"].split(".")[0])
    if any(normalize(k) == p.key for k in dists):
        probe_mods |= set(p.modules[:3])
    a.import_probes = [envmod.import_probe(e, m, root) for m in sorted(probe_mods)]

    # residual references to the old package after a replace/remove decision
    if plan.get("decision") in ("replace", "remove"):
        s = scan(root)
        old = set(p.modules) or {p.key.replace("-", "_")}
        a.residual_usages = [{"file": u.file, "line": u.line, "code": u.code}
                             for u in s.usages if u.module in old and u.kind in ("import", "from-import")]
        words = {m: {m, *p.console_scripts} for m in old}
        a.residual_usages += [{"file": u.file, "line": u.line, "code": u.code}
                              for u in text_references(root, words)]

    # repository's own tests (AI tests excluded, so the comparison is like for like)
    targets = ["--ignore", ai_rel] if ai_rel else []
    run = envmod.pytest(e, root, f"candidate:{p.key}", work / "candidate-junit.xml", targets)
    a.tests = run.to_dict()
    base = b.tests.outcome_map() if b.tests else {}
    base_msg = {c.id: c.message for c in b.tests.cases} if b.tests else {}
    cand = run.outcome_map()
    cand_msg = {c.id: c.message for c in run.cases}
    ok = lambda o: o in ("passed", "skipped")
    fixed = [t for t, o in cand.items() if ok(o) and t in base and not ok(base[t])]
    regress = {t: cand_msg.get(t, "")[:300] for t, o in cand.items() if not ok(o) and ok(base.get(t, "passed"))}
    still = {t: cand_msg.get(t, "")[:300] for t, o in cand.items() if not ok(o) and t in base and not ok(base[t])}
    missing = [t for t in base if t not in cand]
    base_w = [w for w in p.warnings if w.get("run") == "baseline"]
    rem_w = _warnings_for(run, p, mod_to_dist, b.scan.usages, root) if run.cases else []
    owned_failures = {t["test"] for t in p.failing_tests}
    a.comparison = {
        "baseline_counts": b.tests.counts() if b.tests else {},
        "candidate_counts": run.counts(),
        "fixed": fixed, "regressions": regress, "still_failing": still,
        "missing_tests": missing,
        "owned_failures_resolved": sorted(owned_failures & set(fixed)),
        "owned_failures_unresolved": sorted(owned_failures - set(fixed)),
        "baseline_warnings_for_dep": len(base_w),
        "remaining_warnings": rem_w,
        "collection_error": run.collection_error,
    }

    # AI-written tests: run against the ORIGINAL dependency set and the candidate
    if ai_rel:
        cres = envmod.pytest(e, root, f"ai-tests-candidate:{p.key}", work / "ai-candidate-junit.xml", [ai_rel])
        broot = work / "baseline-with-ai-tests"
        copy_repo(b.repo, broot)
        (broot / ai_rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / ai_rel, broot / ai_rel)
        bres = envmod.pytest(b.env, broot, f"ai-tests-baseline:{p.key}", work / "ai-baseline-junit.xml", [ai_rel])
        a.ai_tests = {"file": ai_rel, "candidate": cres.to_dict(), "original": bres.to_dict(),
                      "code": (root / ai_rel).read_text(encoding="utf-8")}

    # verdict
    reasons = []
    if any(not x["applied"] for x in a.edits):
        reasons.append(f"{sum(not x['applied'] for x in a.edits)} code edit(s) could not be applied")
    if regress:
        reasons.append(f"{len(regress)} regression(s) vs baseline")
    if missing:
        reasons.append(f"{len(missing)} baseline test(s) no longer collected")
    if run.collection_error:
        reasons.append("test collection error")
    if a.comparison["owned_failures_unresolved"]:
        reasons.append("baseline failures caused by this dependency still fail")
    if any(not pr["ok"] for pr in a.import_probes if pr["module"] not in p.modules):
        reasons.append("replacement does not import")
    if any(not pr["ok"] for pr in a.import_probes if pr["module"] in p.modules) and \
            plan.get("decision") not in ("replace", "remove"):
        reasons.append("package still fails to import")
    if rem_w:
        reasons.append(f"{len(rem_w)} warning(s) still attributed to this dependency")
    if a.residual_usages:
        reasons.append("old package still imported after replace/remove")
    if not pc.ok:
        reasons.append("pip check reports broken requirements")
    ai_c = (a.ai_tests.get("candidate") or {}).get("counts", {})
    if ai_c and (ai_c.get("failed") or ai_c.get("error")):
        reasons.append("some AI-written tests fail on the candidate")
    if any(not c["passed"] for c in a.plan_checks):
        reasons.append("plan references a package that does not exist")
    hard = regress or missing or run.collection_error or any("does not import" in r or "exist" in r for r in reasons)
    a.verdict = "failed" if hard else ("verified" if not reasons else "partial")
    a.verdict_reasons = reasons or ["no regressions; every baseline problem attributed to this dependency is resolved"]
    return a


@dataclass
class Migration:
    profile: DepProfile
    attempts: list[Attempt]
    error: str = ""

    @property
    def final(self) -> Attempt | None:
        done = [a for a in self.attempts if a.plan]
        if not done:
            return None
        rank = {"verified": 0, "partial": 1, "failed": 2, "not-executed": 3}
        return sorted(done, key=lambda a: (rank[a.verdict], -a.number))[0]


def migrate(b: Baseline, p: DepProfile, gemma: Gemma, python_cmd: str, installer: str,
            max_attempts: int, log) -> Migration:
    m = Migration(p, [])
    work = b.work / "candidates" / p.key
    base_prompt = plan_prompt(build_context(b, p))
    prompt, prev = base_prompt, None
    for n in range(1, max_attempts + 1):
        try:
            ex = gemma.ask_json(prompt)
        except GemmaError as e:
            m.error = str(e)
            log(f"  {p.name}: Gemma error: {e}")
            break
        a = Attempt(n, {"model": ex.model, "backend": ex.backend, "seconds": ex.seconds,
                        "prompt": ex.prompt, "raw_response": ex.raw_response, "usage": ex.usage,
                        "error": ex.error}, ex.parsed)
        m.attempts.append(a)
        if not ex.parsed:
            log(f"  {p.name}: attempt {n} returned no usable JSON")
            continue
        a.plan_checks = _check_plan(ex.parsed, b.work / "registry-cache")
        log(f"  {p.name}: attempt {n} plan = {ex.parsed.get('decision')} -> "
            f"{(ex.parsed.get('replacement') or {}).get('package') or (ex.parsed.get('replacement') or {}).get('stdlib_module') or '-'}"
            f" ({ex.seconds}s); verifying")
        verify(b, p, ex.parsed, work / f"attempt-{n}", python_cmd, installer, a, log)
        c = a.comparison
        log(f"  {p.name}: attempt {n} -> {a.verdict.upper()} "
            f"(tests {c.get('candidate_counts', {})}; {'; '.join(a.verdict_reasons)})")
        if a.verdict == "verified" or ex.parsed.get("decision") == "keep":
            break
        prev = ex.parsed
        prompt = repair_prompt(base_prompt, prev, _feedback(a))
    return m


def combined(b: Baseline, migrations: list[Migration], python_cmd: str, installer: str, log) -> dict:
    """Apply every verified plan together and run the suite once more."""
    chosen = [m for m in migrations if m.final and m.final.verdict == "verified"]
    if not chosen:
        return {"applied": [], "note": "no verified plans to combine"}
    work = b.work / "combined"
    root = work / "repo"
    copy_repo(b.repo, root)
    notes = []
    for m in chosen:
        plan = m.final.plan
        ed = apply_code_edits(root, plan.get("code_edits"))
        rl = apply_requirement_changes(root, plan.get("requirement_changes"), m.profile, b.requirement_files)
        _write_ai_tests(root, m.profile.key, plan.get("suggested_tests"))
        notes.append({"dependency": m.profile.name,
                      "edits_applied": sum(x["applied"] for x in ed), "edits_total": len(ed),
                      "edit_problems": [x for x in ed if not x["applied"]],
                      "requirement_changes": rl})
    e, r = envmod.create(work / "venv", python_cmd, installer)
    r = _install_candidate(e, root, b.requirement_files)
    out = {"applied": notes, "install_ok": r.ok, "install_output": r.tail(20)}
    if r.ok:
        run = envmod.pytest(e, root, "combined", work / "combined-junit.xml")
        out["tests"] = run.to_dict()
        out["versions"] = {k: v["version"] for k, v in envmod.inventory(e).get("dists", {}).items()}
        log(f"combined migration of {len(chosen)} verified plan(s): tests {run.counts()}, "
            f"{len(run.warnings)} distinct warnings")
    out["diff"] = unified_diff(b.repo, root)
    out["repo_path"] = str(root)
    return out
