"""DepExit command line.

    python -m depexit analyze https://github.com/rishrek/LinkWatch
    python -m depexit analyze ./some/local/repo --only jinja2,nose
    python -m depexit replay capsule-out/capsules/jinja2/capsule.json
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from . import env as envmod

DEFAULT_TARGET = "https://github.com/rishrek/LinkWatch"


def log(msg: str) -> None:
    print(f"[depexit {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _resolve(cmd: list[str]) -> str | None:
    """Return the real interpreter path for a launcher command, if it is 3.12 or 3.13."""
    r = envmod.run([*cmd, "-c", "import sys; print(sys.executable); print('%d.%d' % sys.version_info[:2])"], timeout=30)
    if not r.ok:
        return None
    lines = r.stdout.strip().splitlines()
    return lines[0] if len(lines) == 2 and lines[1] in ("3.12", "3.13") else None


ECOSYSTEMS = [
    ("Python", ("requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "poetry.lock")),
    ("Node.js / JavaScript", ("package.json",)),
    ("Go", ("go.mod",)),
    ("Rust", ("Cargo.toml",)),
    ("Java / Kotlin", ("pom.xml", "build.gradle", "build.gradle.kts")),
    ("Ruby", ("Gemfile",)),
    ("PHP", ("composer.json",)),
    (".NET", ("*.csproj", "*.sln")),
]


def detect_ecosystems(repo: Path) -> dict[str, list[str]]:
    """Which package ecosystems a repository uses, judged by manifest files at its root."""
    found: dict[str, list[str]] = {}
    for name, patterns in ECOSYSTEMS:
        hits = sorted({p.name for pat in patterns for p in repo.glob(pat)})
        if name == "Python":
            hits += sorted(p.name for p in repo.glob("requirements*.txt") if p.name not in hits)
        if hits:
            found[name] = hits
    return found


def write_unsupported(out: Path, target: dict, eco: dict) -> None:
    """A truthful report for a repository DepExit cannot analyse yet."""
    from html import escape as e
    from .report_html import CSS
    out.mkdir(parents=True, exist_ok=True)
    found = ", ".join(f"{k} ({', '.join(v)})" for k, v in eco.items()) or "no recognised dependency manifest"
    msg = (f"This repository is not a Python project. Detected: {found}. "
           "DepExit currently analyses Python repositories only; nothing was installed, tested or sent to the model.")
    index = {"target": target, "supported": False, "ecosystems": eco, "message": msg, "dependencies": []}
    (out / "capsule-index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    (out / "SUMMARY.md").write_text(f"# DepExit run on `{target['source']}`\n\n{msg}\n", encoding="utf-8")
    (out / "report.html").write_text(
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>DepExit Report</title><style>{CSS}</style></head><body><main><h1>Dependency Exit Report</h1>"
        f"<div class='meta'><code>{e(target['source'])}</code> @ <code>{e((target.get('commit') or '')[:10])}</code></div>"
        f"<div class='box' style='margin-top:24px'><b>Not analysed: unsupported ecosystem.</b><p>{e(msg)}</p></div>"
        f"</main></body></html>", encoding="utf-8")


def find_python(pref: str | None) -> str:
    """Find a Python 3.12/3.13 for the target. Accepts paths or launchers like 'py -3.12'."""
    import shlex
    if pref:
        exe = _resolve(shlex.split(pref, posix=os.name != "nt"))
        if not exe:
            raise SystemExit(f"--python {pref!r} is not a working Python 3.12 or 3.13 interpreter")
        return exe
    candidates = [["python3.12"], ["python3.13"], ["py", "-3.12"], ["py", "-3.13"]]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            exe = _resolve(cmd)
            if exe:
                return exe
    if sys.version_info[:2] in ((3, 12), (3, 13)):
        return sys.executable
    if shutil.which("uv"):
        # uv can provide a managed CPython without touching the system Python
        for ver in ("3.12", "3.13"):
            r = envmod.run(["uv", "python", "find", ver], timeout=60)
            if not r.ok:
                print(f"[depexit] no Python {ver} found, fetching one with uv ...", flush=True)
                envmod.run(["uv", "python", "install", ver], timeout=600)
                r = envmod.run(["uv", "python", "find", ver], timeout=60)
            if r.ok and r.stdout.strip():
                exe = _resolve([r.stdout.strip().splitlines()[-1]])
                if exe:
                    return exe
    raise SystemExit("Need Python 3.12 or 3.13 for the target repo (LinkWatch does not support 3.14). "
                     "Install it (fastest: install uv, then DepExit fetches 3.12 itself), or pass "
                     "--python /path/to/python3.12 (Windows: --python \"py -3.12\")")


def prepare_target(target: str, work: Path) -> tuple[Path, dict]:
    dst = work / "target"
    if dst.exists():
        shutil.rmtree(dst)
    if target.startswith(("http://", "https://", "git@")):
        e = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        r = envmod.run(["git", "clone", "--quiet", "--depth", "1", target, dst], timeout=600, env=e)
        if not r.ok:
            hint = ("repository not found, or it is private (DepExit clones public repositories; "
                    "for a private one, clone it yourself and pass the local folder)"
                    if "Username" in r.tail() or "not found" in r.tail().lower() else r.tail())
            raise SystemExit(f"could not clone {target}: {hint}")
    else:
        src = Path(target).resolve()
        if not src.is_dir():
            raise SystemExit(f"target not found: {target}")
        from .migrate import copy_repo
        copy_repo(src, dst)
        if (src / ".git").exists():
            r = envmod.run(["git", "rev-parse", "HEAD"], cwd=src)
            (dst / ".depexit-commit").write_text(r.stdout.strip() if r.ok else "", encoding="utf-8")
    commit = ""
    r = envmod.run(["git", "rev-parse", "HEAD"], cwd=dst)
    if r.ok and (dst / ".git").exists():
        commit = r.stdout.strip()
    elif (dst / ".depexit-commit").exists():
        commit = (dst / ".depexit-commit").read_text().strip()
        (dst / ".depexit-commit").unlink()
    return dst, {"source": target, "commit": commit}


def make_gemma(args):
    from .gemma import Gemma, GemmaError
    backend = args.ai
    if backend == "auto":
        backend = "google" if (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")) else "none"
        if backend == "none":
            log("no GEMINI_API_KEY set: running evidence-only (no AI proposals). Use --ai ollama for a local model.")
    if backend == "none":
        return None
    try:
        return Gemma(backend, args.model, ollama_url=args.ollama_url)
    except GemmaError as e:
        raise SystemExit(str(e))


def cmd_analyze(args) -> int:
    from .analyze import build_baseline
    from .capsule import write_all
    from .migrate import combined, migrate

    out = Path(args.out).resolve()
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    python_cmd = find_python(args.python)
    installer = envmod.pick_installer(args.installer)
    gemma = make_gemma(args)
    log(f"DepExit {__version__} | target {args.target} | python {python_cmd} | installer {installer} | "
        f"AI {gemma.label if gemma else 'off'}")

    repo, target = prepare_target(args.target, work)
    eco = detect_ecosystems(repo)
    has_py = "Python" in eco or any(repo.rglob("*.py"))
    if not has_py:
        write_unsupported(out, target, eco)
        log(f"not a Python repository (detected: {', '.join(eco) or 'no known manifest'}); "
            f"DepExit supports Python only. Wrote {out / 'report.html'}")
        return 2
    others = [k for k in eco if k != "Python"]
    if others:
        log(f"note: this repository also uses {', '.join(others)}; only its Python dependencies are analysed")
    b = build_baseline(repo, work, python_cmd, installer, not args.no_pyproject_check, log)
    target["python"] = b.inventory.get("python")

    ranked = sorted(b.profiles.values(), key=lambda p: -p.score)
    log("risk ranking (observed + measured):")
    for p in ranked:
        ids = ",".join(i.id for i in p.indicators) or "-"
        log(f"  {'*' if p.at_risk else ' '} {p.name:<18} {p.level:<8} {p.score:>3}  {ids}")

    only = {x.strip().lower() for x in args.only.split(",")} if args.only else None
    selected = [p for p in ranked if (p.key in only if only else p.at_risk)]
    if args.max_deps:
        selected = selected[:args.max_deps]

    migrations = {}
    if gemma and selected:
        log(f"asking {gemma.label} for migration plans: {', '.join(p.name for p in selected)}")
        from concurrent.futures import ThreadPoolExecutor
        workers = max(1, min(args.parallel, len(selected)))
        if workers > 1:
            log(f"running {workers} dependencies in parallel (isolated copies and venvs; --parallel 1 to serialise)")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {p.key: pool.submit(migrate, b, p, gemma, python_cmd, installer, args.attempts, log)
                       for p in selected}
            for key, fut in futures.items():
                migrations[key] = fut.result()
    comb = combined(b, list(migrations.values()), python_cmd, installer, log) if migrations else None

    target["other_ecosystems_not_analysed"] = {k: v for k, v in eco.items() if k != "Python"}
    meta = {"target": target, "settings": {
        "python": python_cmd, "installer": installer, "ai": gemma.label if gemma else "off",
        "attempts": args.attempts, "selected": [p.name for p in selected]}}
    summary = write_all(out, meta, b, migrations, comb, gemma.label if gemma else "off")

    log("done. Results:")
    for d in summary["dependencies"]:
        if d["at_risk"] or d["status"] not in ("not-required",):
            log(f"  {d['dependency']:<18} {d['status']:<14} {d['proposal']}")
    if comb and comb.get("tests"):
        log(f"  combined verified migration: tests {comb['tests']['counts']}")
    log(f"open {out / 'report.html'}  (capsules in {out / 'capsules'})")
    return 0


def cmd_replay(args) -> int:
    """Re-verify a saved capsule's plan against a (possibly newer) checkout, without the model."""
    from .analyze import build_baseline
    from .migrate import Attempt, verify

    cap_path = Path(args.capsule).resolve()
    plan_path = cap_path.parent / "plan.json"
    if not plan_path.exists():
        raise SystemExit(f"{plan_path} not found: only capsules with an AI plan can be replayed")
    cap = json.loads(cap_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    key = cap["dependency"]["key"]
    out = Path(args.out).resolve()
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    python_cmd = find_python(args.python)
    installer = envmod.pick_installer(args.installer)
    target = args.target or cap["target"]["source"]
    log(f"replaying capsule for {cap['dependency']['name']} against {target} (no model call)")
    repo, tmeta = prepare_target(target, work)
    b = build_baseline(repo, work, python_cmd, installer, False, log)
    if key not in b.profiles:
        raise SystemExit(f"{key} is no longer a dependency of the target")
    a = verify(b, b.profiles[key], plan, work / "replay", python_cmd, installer, Attempt(1, {}, plan), log)
    result = {"dependency": cap["dependency"]["name"], "target": tmeta, "verdict": a.verdict,
              "reasons": a.verdict_reasons, "tests": a.comparison,
              "edits": a.edits, "requirement_changes": a.requirement_log}
    (out / f"replay-{key}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    log(f"replay verdict: {a.verdict.upper()} — {'; '.join(a.verdict_reasons)}")
    return 0 if a.verdict == "verified" else 1


def cmd_render(args) -> int:
    """Rebuild report.html from a finished run's capsules, without re-running anything."""
    from .report_html import page
    out = Path(args.dir).resolve()
    index = json.loads((out / "capsule-index.json").read_text(encoding="utf-8"))
    caps = []
    for d in index["dependencies"]:
        caps.append(json.loads((out / d["capsule"]).read_text(encoding="utf-8")))
    (out / "report.html").write_text(page(index, caps), encoding="utf-8")
    log(f"rebuilt {out / 'report.html'} from {len(caps)} capsules")
    return 0


def cmd_doctor(args) -> int:
    """Pre-flight check: interpreters, git, registry access and a tiny Gemma call."""
    ok = True

    def line(good, what, detail=""):
        nonlocal ok
        ok &= bool(good)
        print(f"  [{'ok' if good else 'XX'}] {what}{(' - ' + detail) if detail else ''}")

    print(f"DepExit {__version__} doctor (running on Python {sys.version.split()[0]})")
    line(sys.version_info >= (3, 11), "DepExit runs on Python >= 3.11")
    try:
        py = find_python(args.python)
        r = envmod.run([py, "--version"])
        line(r.ok, f"target interpreter {py}", (r.stdout or r.stderr).strip())
    except SystemExit as e:
        line(False, "target interpreter", str(e))
    line(shutil.which("git"), "git available")
    line(True, f"installer: {envmod.pick_installer('auto')}", "uv is faster; pip works")
    from . import pypi
    import tempfile
    exists, latest = pypi.exists("jinja2", Path(tempfile.mkdtemp()))
    line(exists, "PyPI JSON API reachable", f"jinja2 latest {latest}" if exists else "")
    try:
        g = make_gemma(args)
        if g is None:
            line(False, "Gemma", "AI disabled (set GEMINI_API_KEY or use --ai ollama)")
        else:
            ex = g.ask_json('Reply with exactly this JSON and nothing else: {"status": "ok"}')
            line(ex.parsed is not None, f"Gemma call answered by {g.label} (model id from the API request)",
                 f"{ex.seconds}s -> {ex.raw_response.strip()[:120]}")
    except Exception as e:  # noqa: BLE001 - doctor reports everything
        line(False, "Gemma call", str(e)[:300])
    print("ready" if ok else "fix the XX items above")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="depexit", description="Evidence-first dependency exit planning with Gemma 4.")
    ap.add_argument("--version", action="version", version=f"depexit {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--python", help="interpreter for the target repo (default: python3.12, then python3.13)")
        p.add_argument("--installer", default="auto", choices=["auto", "pip", "uv"])
        p.add_argument("--out", default="capsule-out", help="output directory (default: capsule-out)")

    a = sub.add_parser("analyze", help="analyse a repository and write Dependency Exit Capsules")
    a.add_argument("target", nargs="?", default=DEFAULT_TARGET, help="git URL or local path (default: LinkWatch)")
    a.add_argument("--ai", default="auto", choices=["auto", "google", "ollama", "none"],
                   help="auto = google if GEMINI_API_KEY is set, else none")
    a.add_argument("--model", help="model id (default gemma-4-31b-it for google, gemma4 for ollama)")
    a.add_argument("--ollama-url", default="http://localhost:11434")
    a.add_argument("--only", help="comma-separated dependency names to migrate (default: all at-risk)")
    a.add_argument("--max-deps", type=int, default=0)
    a.add_argument("--attempts", type=int, default=2, help="plan + repair attempts per dependency (default 2)")
    a.add_argument("--parallel", type=int, default=3, help="dependencies migrated concurrently (default 3)")
    a.add_argument("--no-pyproject-check", action="store_true", help="skip the second install via pyproject.toml")
    common(a)
    a.set_defaults(func=cmd_analyze)

    r = sub.add_parser("replay", help="re-verify a saved capsule without calling the model")
    r.add_argument("capsule", help="path to capsules/<dep>/capsule.json")
    r.add_argument("target", nargs="?", help="repo to verify against (default: the capsule's original target)")
    common(r)
    r.set_defaults(func=cmd_replay, out="replay-out")

    rr = sub.add_parser("render", help="rebuild report.html from an existing run folder (no re-run)")
    rr.add_argument("dir", help="a run folder, e.g. capsule-out or examples/linkwatch-run")
    rr.set_defaults(func=cmd_render)

    d = sub.add_parser("doctor", help="check interpreters, network and Gemma access before a run")
    d.add_argument("--python")
    d.add_argument("--ai", default="auto", choices=["auto", "google", "ollama", "none"])
    d.add_argument("--model")
    d.add_argument("--ollama-url", default="http://localhost:11434")
    d.set_defaults(func=cmd_doctor)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
