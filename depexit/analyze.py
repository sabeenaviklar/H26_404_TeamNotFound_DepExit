"""Phase 1: build an evidence profile for every dependency, with no AI involved.

Combines static inspection (manifests, AST), execution (installs, import
probes, the repository's own test suite) and registry metadata into risk
indicators. Every indicator carries the evidence that produced it.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path

from . import env as envmod
from . import pypi
from .manifest import Manifest, normalize, read_manifest, spec_conflicts
from .scan import ScanResult, Usage, scan, text_references

SEVERITY_POINTS = {"critical": 40, "high": 20, "medium": 10, "low": 3}
STALE_DAYS = 730
OLD_PIN_DAYS = 1095


@dataclass
class Indicator:
    id: str
    severity: str
    title: str
    evidence: str
    source: str      # observed:static | observed:registry | measured:execution


@dataclass
class DepProfile:
    key: str
    name: str
    declared: list[dict]
    installed_version: str | None
    modules: list[str]
    console_scripts: list[str]
    relation: str                    # direct | transitive | undeclared | stdlib-shim
    usages: list[dict] = field(default_factory=list)
    import_probes: list[dict] = field(default_factory=list)
    failing_tests: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    registry: dict = field(default_factory=dict)
    indicators: list[Indicator] = field(default_factory=list)

    @property
    def score(self) -> int:
        return sum(SEVERITY_POINTS[i.severity] for i in self.indicators)

    @property
    def level(self) -> str:
        sev = {i.severity for i in self.indicators}
        for s in ("critical", "high", "medium", "low"):
            if s in sev:
                return s
        return "none"

    @property
    def at_risk(self) -> bool:
        return self.level in ("critical", "high") or self.score >= 20

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(score=self.score, level=self.level, at_risk=self.at_risk)
        return d


@dataclass
class Baseline:
    repo: Path
    work: Path
    manifest: Manifest
    scan: ScanResult
    env: envmod.Env
    install_ok: bool
    install_error: str
    inventory: dict
    pip_check: dict
    tests: envmod.TestRun | None
    alt: dict | None
    profiles: dict[str, DepProfile]
    conflicts: list[dict]
    requirement_files: list[str]


def _req_files(repo: Path, man: Manifest) -> list[str]:
    return [f for f in man.files if f.endswith(".txt")]


def _attribute_warning(w: dict, mod_to_dist: dict, usages: list[Usage], repo: Path | None = None) -> str | None:
    f = w["file"]
    if repo is not None:
        root = str(repo).rstrip("/\\") + "/"
        if f.replace("\\", "/").startswith(root.replace("\\", "/")):
            f = w["file"] = f[len(root):]
    if f.startswith("site-packages/"):
        top = f.split("/")[1].removesuffix(".py")
        return mod_to_dist.get(top)
    # A warning raised at a repo line that imports or uses a third-party module
    for u in usages:
        if u.file == f and str(u.line) == str(w["line"]):
            return mod_to_dist.get(u.module)
    for mod, dist in mod_to_dist.items():
        if len(mod) > 3 and mod in w["msg"]:
            return dist
    return None


def build_baseline(repo: Path, work: Path, python_cmd: str, installer: str,
                   check_pyproject: bool, log) -> Baseline:
    man = read_manifest(repo)
    sres = scan(repo)
    log(f"manifests: {', '.join(man.files) or 'none'}; {len(man.declarations)} declarations, "
        f"{len(sres.python_files)} python files")

    env, r = envmod.create(work / "venv-baseline", python_cmd, installer)
    if not r.ok:
        raise SystemExit(f"could not create venv with {python_cmd}:\n{r.tail()}")
    req_files = _req_files(repo, man)
    if req_files:
        args = []
        for f in req_files:
            args += ["-r", f]
        r = envmod.install(env, args, repo, "install:baseline")
    else:
        r = envmod.install(env, [".", "pytest"], repo, "install:baseline")
    install_ok, install_error = r.ok, "" if r.ok else r.tail(30)
    log(f"baseline install ({env.installer}): {'ok' if r.ok else 'FAILED'} in {r.seconds}s")
    if not r.ok:
        # keep going with whatever we could install so the capsule still shows evidence
        envmod.install(env, ["pytest"], repo, "install:pytest-fallback")
    pc = envmod.pip_check(env)
    inv = envmod.inventory(env)
    dists = inv.get("dists", {})
    mod_to_dist: dict[str, str] = {}
    for dname, d in dists.items():
        for m in d["modules"]:
            mod_to_dist.setdefault(m, dname)

    tests = envmod.pytest(env, repo, "baseline", work / "evidence" / "baseline-junit.xml")
    c = tests.counts()
    log(f"baseline tests: {c['passed']} passed, {c['failed']} failed, {c['error']} errors, "
        f"{len(tests.warnings)} distinct warnings")

    alt = None
    pp = repo / "pyproject.toml"
    if check_pyproject and req_files and pp.exists() and "pyproject.toml" in man.files:
        aenv, r = envmod.create(work / "venv-pyproject", python_cmd, installer)
        dev = [a for f in req_files if "dev" in f or "test" in f for a in ("-r", f)]
        r = envmod.install(aenv, [".", *dev] if dev else [".", "pytest"], repo, "install:pyproject")
        ainv = envmod.inventory(aenv) if r.ok else {"dists": {}}
        atests = envmod.pytest(aenv, repo, "pyproject-install", work / "evidence" / "pyproject-junit.xml") if r.ok else None
        alt = {"install_ok": r.ok, "install_error": "" if r.ok else r.tail(20),
               "versions": {k: v["version"] for k, v in ainv.get("dists", {}).items()},
               "tests": atests.to_dict() if atests else None, "log": aenv.log}
        log(f"pyproject install path: {'ok' if r.ok else 'FAILED'}"
            + (f", tests {atests.counts()}" if atests else ""))

    profiles = _profiles(repo, man, sres, env, dists, mod_to_dist, tests, alt, work, log)
    return Baseline(repo, work, man, sres, env, install_ok, install_error, inv,
                    {"ok": pc.ok, "output": pc.tail(20)}, tests, alt, profiles,
                    spec_conflicts(man), req_files)


def _profiles(repo, man, sres, env, dists, mod_to_dist, tests, alt, work, log):
    by_key = man.by_key()
    dist_by_key = {normalize(n): n for n in dists}
    profiles: dict[str, DepProfile] = {}

    def ensure(key: str, relation: str) -> DepProfile:
        if key in profiles:
            return profiles[key]
        dname = dist_by_key.get(key)
        d = dists.get(dname, {}) if dname else {}
        p = DepProfile(
            key=key, name=dname or (by_key[key][0].name if key in by_key else key),
            declared=[{"file": x.file, "line": x.line, "spec": x.spec or "*", "group": x.group,
                       "raw": x.raw} for x in by_key.get(key, [])],
            installed_version=d.get("version"), modules=d.get("modules", []),
            console_scripts=d.get("console_scripts", []), relation=relation)
        profiles[key] = p
        return p

    for key in by_key:
        ensure(key, "direct")
    # undeclared imports
    for mod in sorted(sres.modules()):
        dname = mod_to_dist.get(mod)
        key = normalize(dname) if dname else normalize(mod)
        if key not in by_key:
            ensure(key, "undeclared")

    # transitive dists implicated in failing tests
    failing = [t for t in tests.cases if t.outcome in ("failed", "error")] if tests else []
    for t in failing:
        for mod in envmod.modules_in_traceback(t.detail + "\n" + t.message):
            dname = mod_to_dist.get(mod)
            if dname and normalize(dname) not in profiles:
                ensure(normalize(dname), "transitive")

    # static usage
    needles = {}
    for p in profiles.values():
        mods = p.modules or [p.key.replace("-", "_")]
        for u in sres.for_modules(mods):
            p.usages.append(asdict(u))
        needles.update({m: {m, *p.console_scripts} for m in mods})
    for u in text_references(repo, needles):
        dname = mod_to_dist.get(u.module)
        key = normalize(dname) if dname else normalize(u.module)
        if key in profiles:
            profiles[key].usages.append(asdict(u))

    # import probes for each module of declared / undeclared deps
    for p in profiles.values():
        for m in p.modules[:4]:
            p.import_probes.append(envmod.import_probe(env, m, repo))

    # attribute failing tests and warnings
    for t in failing:
        mods = envmod.modules_in_traceback(t.detail + "\n" + t.message)
        for mod in mods:
            dname = mod_to_dist.get(mod)
            if dname and normalize(dname) in profiles:
                profiles[normalize(dname)].failing_tests.append(
                    {"test": t.id, "message": t.message[:400], "implicated_modules": mods})
    for w in (tests.warnings if tests else []):
        dname = _attribute_warning(w, mod_to_dist, sres.usages, repo)
        if dname and normalize(dname) in profiles:
            profiles[normalize(dname)].warnings.append({**w, "run": "baseline"})
    if alt and alt.get("tests"):
        for w in alt["tests"]["warnings"]:
            dname = _attribute_warning(w, mod_to_dist, sres.usages, repo)
            if dname and normalize(dname) in profiles:
                profiles[normalize(dname)].warnings.append({**w, "run": "pyproject-install"})

    cache = work / "registry-cache"
    for p in profiles.values():
        p.registry = pypi.package_facts(p.name, p.installed_version, cache)
    log(f"registry metadata fetched for {len(profiles)} packages")

    conflicts = {c["package"]: c for c in spec_conflicts(man)}
    for p in profiles.values():
        _indicators(p, conflicts.get(p.key), alt, sres)
    return profiles


def _indicators(p: DepProfile, conflict, alt, sres):
    add = p.indicators.append
    code_uses = [u for u in p.usages if u["kind"] != "text"]
    text_uses = [u for u in p.usages if u["kind"] == "text"]

    for probe in p.import_probes:
        if not probe["ok"]:
            add(Indicator("IMPORT_FAILS", "critical", f"`import {probe['module']}` fails on the target Python",
                          probe["error"], "measured:execution"))
    if p.failing_tests:
        ids = ", ".join(sorted({t["test"] for t in p.failing_tests}))
        add(Indicator("TEST_FAILURES", "critical", f"{len(p.failing_tests)} repository test(s) fail inside this package",
                      f"{ids}: {p.failing_tests[0]['message'][:200]}", "measured:execution"))
    if p.warnings:
        w = p.warnings[0]
        add(Indicator("DEPRECATION_WARNINGS", "medium", f"{len(p.warnings)} warning(s) raised during the test run",
                      f"{w['file']}:{w['line']} {w['cat']}: {w['msg'][:200]} (run: {w['run']})", "measured:execution"))
    if conflict:
        specs = "; ".join(f"{d['file']}:{d['line']} {d['spec']}" for d in conflict["declarations"])
        add(Indicator("SPEC_CONFLICT", "high", "Declared with different version constraints in different manifests",
                      specs, "observed:static"))
        if alt and alt.get("versions"):
            v = {pypi_key: ver for pypi_key, ver in alt["versions"].items() if normalize(pypi_key) == p.key}
            if v:
                p.indicators[-1].evidence += f"; installing via pyproject resolves to {list(v.values())[0]} " \
                                             f"vs {p.installed_version} via requirements"
    if p.relation == "undeclared":
        where = ", ".join(sorted({f"{u['file']}:{u['line']}" for u in code_uses})) or "n/a"
        add(Indicator("UNDECLARED", "high", "Imported by the code but not declared in any manifest",
                      f"imported at {where}; only installed transitively", "observed:static"))
    if p.relation == "transitive":
        add(Indicator("TRANSITIVE_BREAKAGE", "high", "Undeclared transitive dependency implicated in a failure",
                      f"resolved to {p.installed_version}, appears in failing traceback(s)", "measured:execution"))
    if p.relation == "direct" and not code_uses and not text_uses:
        add(Indicator("UNUSED", "medium" if any(d["spec"].startswith("==") for d in p.declared) else "low",
                      "Declared but never imported or invoked by the repository",
                      "no import, reference or CLI invocation found in code, Makefile, Dockerfile or CI files",
                      "observed:static"))
    elif p.relation == "direct" and not code_uses and text_uses:
        u = text_uses[0]
        add(Indicator("TOOLING_ONLY", "low", "Used only from build or CI files",
                      f"{u['file']}:{u['line']} `{u['code']}`", "observed:static"))
    priv = [u for u in code_uses if u["kind"] == "private-api"]
    if priv:
        add(Indicator("PRIVATE_API", "medium", "Relies on a private (underscore) API that can change without notice",
                      "; ".join(f"{u['file']}:{u['line']} {u['symbol']}" for u in priv), "observed:static"))
    mp = [u for u in code_uses if u["kind"] == "monkeypatch"]
    if mp:
        add(Indicator("MONKEYPATCH", "medium", "Monkeypatches the library at import time",
                      "; ".join(f"{u['file']}:{u['line']} {u['symbol']}" for u in mp), "observed:static"))
    if p.relation == "direct" and all(d["spec"] in ("*", "") for d in p.declared):
        add(Indicator("UNPINNED", "low", "No version constraint, so installs are not reproducible",
                      "; ".join(f"{d['file']}:{d['line']}" for d in p.declared), "observed:static"))

    r = p.registry
    if not r.get("available"):
        return
    if r.get("repo_archived"):
        add(Indicator("REPO_ARCHIVED", "high", "Upstream source repository is archived (read-only)",
                      f"github.com/{r['github']} archived; last push {r.get('repo_last_push')}", "observed:registry"))
    days = r.get("days_since_latest_release")
    if days is not None and days > STALE_DAYS:
        add(Indicator("STALE_UPSTREAM", "high" if days > 3 * 365 else "medium",
                      f"No release in {days // 365} year(s)",
                      f"latest {r['latest_version']} released {r['latest_release_date']}", "observed:registry"))
    if r.get("inactive_classifier"):
        add(Indicator("INACTIVE", "high", "Package marked 'Development Status :: Inactive' on PyPI",
                      r["source_url"], "observed:registry"))
    if r.get("installed_yanked"):
        add(Indicator("YANKED", "high", "Installed version is yanked on PyPI",
                      f"{p.installed_version}", "observed:registry"))
    mb = r.get("major_versions_behind")
    if mb and mb > 0 and any(d["spec"].startswith("==") for d in p.declared):
        add(Indicator("OUTDATED_PIN", "medium", f"Pinned {mb} major version(s) behind latest",
                      f"pinned {p.installed_version} ({r.get('installed_release_date')}), latest {r['latest_version']}",
                      "observed:registry"))
    elif (r.get("installed_age_days") or 0) > OLD_PIN_DAYS and any(d["spec"].startswith("==") for d in p.declared):
        add(Indicator("OLD_PIN", "low", "Pinned to a release older than 3 years",
                      f"{p.installed_version} released {r.get('installed_release_date')}, latest {r['latest_version']}",
                      "observed:registry"))
