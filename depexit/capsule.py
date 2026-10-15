"""Phase 3: write Dependency Exit Capsules.

Every field in a capsule carries a provenance tag:

  observed   read from the repository or a package registry, no execution
  measured   produced by running something (install, import, tests)
  ai         proposed by Gemma 4 and NOT trusted on its own
  verified   an AI proposal that DepExit applied and confirmed by execution

A capsule is plain JSON plus a Markdown rendering and a patch, so it can be
committed next to the code, reviewed in a pull request, and re-verified
later with ``depexit replay`` without calling the model again.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import __version__

LIMITATIONS = [
    "Verification is only as strong as the repository's own test suite plus the AI-written tests; "
    "code paths no test exercises are not proven safe.",
    "Each dependency is verified in isolation, then all verified plans are applied together once; "
    "other combinations are not tested.",
    "Risk signals from PyPI and GitHub reflect the moment of the run and the public metadata available.",
    "Security advisories are out of scope for this challenge and are not checked.",
]


def _ts():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slug(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def dependency_capsule(meta: dict, b, p, mig) -> dict:
    final = mig.final if mig else None
    plan = final.plan if final else None
    verdict = final.verdict if final else ("not-attempted" if p.at_risk else "not-required")
    cap = {
        "capsule_version": "1.0",
        "generated_at": _ts(),
        "generator": f"depexit {__version__}",
        "target": meta["target"],
        "provenance_legend": {
            "observed": "read from repository files or package registries; no execution",
            "measured": "produced by executing installs, imports or tests",
            "ai": "proposed by the model; not trusted until verified",
            "verified": "AI proposal applied by DepExit and confirmed by execution",
        },
        "dependency": {
            "provenance": "observed", "name": p.name, "key": p.key, "relation": p.relation,
            "installed_version": p.installed_version, "declared": p.declared,
            "import_names": p.modules, "console_scripts": p.console_scripts,
        },
        "risk": {
            "provenance": "observed+measured", "level": p.level, "score": p.score, "at_risk": p.at_risk,
            "indicators": [{"id": i.id, "severity": i.severity, "title": i.title,
                            "evidence": i.evidence, "provenance": i.source} for i in p.indicators],
        },
        "usage_locations": {"provenance": "observed", "items": p.usages},
        "registry": {"provenance": "observed", **p.registry},
        "baseline_execution": {
            "provenance": "measured",
            "import_probes": p.import_probes,
            "failing_tests": p.failing_tests,
            "warnings": p.warnings,
        },
    }
    if mig is None:
        cap["status"] = verdict
        cap["open_concerns"] = [{"provenance": "observed",
                                 "text": "Not selected for migration (below risk threshold or excluded by --only)."}]
        return cap
    if mig.error and not plan:
        cap["status"] = "ai-unavailable"
        cap["open_concerns"] = [{"provenance": "measured", "text": f"Model call failed: {mig.error}"}]
        return cap
    if not plan:
        cap["status"] = "no-usable-plan"
        cap["open_concerns"] = [{"provenance": "measured", "text": "Model returned no parseable plan."}]
        return cap

    ver = final.verdict == "verified"
    rep = plan.get("replacement") or {}
    cap["status"] = verdict
    cap["proposed_replacement"] = {
        "provenance": "verified" if ver else "ai",
        "decision": plan.get("decision"), "package": rep.get("package"),
        "version_spec": rep.get("version_spec"), "stdlib_module": rep.get("stdlib_module"),
        "rationale": plan.get("rationale"), "model_confidence": plan.get("confidence"),
        "plan_checks": final.plan_checks,
    }
    cap["migration_steps"] = {"provenance": "verified" if ver else "ai",
                              "steps": plan.get("migration_steps") or [],
                              "code_edits": final.edits, "requirement_changes": final.requirement_log,
                              "patch_file": "patch.diff"}
    ai_t = final.ai_tests
    cap["suggested_tests"] = {
        "provenance": "ai",
        "tests": [{"name": t.get("name"), "purpose": t.get("purpose")} for t in plan.get("suggested_tests") or []],
        "file": ai_t.get("file"),
        "executed": bool(ai_t),
    }
    cmp = final.comparison
    cap["executed_test_results"] = {
        "provenance": "measured",
        "install": final.install,
        "candidate_versions": {k: v for k, v in final.candidate_versions.items()},
        "import_probes": final.import_probes,
        "residual_usages_of_old_package": final.residual_usages,
        "repository_tests": {
            "baseline": cmp.get("baseline_counts"), "candidate": cmp.get("candidate_counts"),
            "fixed": cmp.get("fixed") or [], "regressions": cmp.get("regressions") or {},
            "still_failing": cmp.get("still_failing") or {}, "missing": cmp.get("missing_tests") or [],
        },
        "risk_indicators_after_change": cmp.get("indicators") or [],
        "ai_written_tests": {
            "against_original_dependency": (ai_t.get("original") or {}).get("counts"),
            "against_replacement": (ai_t.get("candidate") or {}).get("counts"),
            "per_test": _ai_matrix(ai_t),
        } if ai_t else None,
        "warnings_attributed_before": cmp.get("baseline_warnings_for_dep") or 0,
        "warnings_attributed_after": len(cmp.get("remaining_warnings") or []),
        "verdict": final.verdict, "verdict_reasons": final.verdict_reasons,
    }
    gaps = []
    for t, msg in (cmp.get("regressions") or {}).items():
        gaps.append({"provenance": "measured", "text": f"Regression: {t}: {msg}"})
    for t, msg in (cmp.get("still_failing") or {}).items():
        gaps.append({"provenance": "measured", "text": f"Still failing (may be another dependency): {t}: {msg}"})
    for w in cmp.get("remaining_warnings") or []:
        gaps.append({"provenance": "measured", "text": f"Warning remains: {w['file']}:{w['line']} {w['cat']}: {w['msg'][:160]}"})
    for e in final.edits:
        if not e["applied"]:
            gaps.append({"provenance": "measured", "text": f"Edit to {e['file']} not applied: {e['reason']}"})
    for row in _ai_matrix(ai_t):
        if row["replacement"] not in ("passed", None):
            gaps.append({"provenance": "measured", "text": f"AI-written test {row['test']} {row['replacement']} on the replacement"})
        elif row["original"] not in ("passed", None) and row["replacement"] == "passed":
            gaps.append({"provenance": "measured",
                         "text": f"Behaviour differs: {row['test']} {row['original']} on the original dependency but passes "
                                 f"on the replacement (expected when the original is broken)"})
    for n in plan.get("compatibility_notes") or []:
        gaps.append({"provenance": "ai", "text": n})
    cap["compatibility_gaps"] = gaps
    concerns = [{"provenance": "ai", "text": r} for r in plan.get("risks") or []]
    if final.verdict != "verified":
        concerns.append({"provenance": "measured", "text": "Not verified: " + "; ".join(final.verdict_reasons)})
    if not ai_t:
        concerns.append({"provenance": "observed", "text": "No AI-written tests were produced for this dependency."})
    concerns += [{"provenance": "observed", "text": t} for t in LIMITATIONS[:2]]
    cap["open_concerns"] = concerns
    cap["attempts"] = [{
        "attempt": a.number, "model": a.exchange.get("model"), "backend": a.exchange.get("backend"),
        "seconds": a.exchange.get("seconds"), "decision": (a.plan or {}).get("decision"),
        "verdict": a.verdict, "reasons": a.verdict_reasons,
    } for a in mig.attempts]
    return cap


def _ai_matrix(ai_t: dict) -> list[dict]:
    if not ai_t:
        return []
    def outcomes(run):
        cases = (run or {}).get("cases", [])
        per = {x["id"].split("::")[-1]: x["outcome"] for x in cases if "::" in x["id"]}
        module_err = next((x for x in cases if "::" not in x["id"] and x["outcome"] != "passed"), None)
        return per, (f"{module_err['outcome']} (module failed to import)" if module_err else None)
    o, o_err = outcomes(ai_t.get("original"))
    c, c_err = outcomes(ai_t.get("candidate"))
    names = sorted(set(o) | set(c))
    return [{"test": n, "original": o.get(n, o_err), "replacement": c.get(n, c_err)} for n in names]


# ------------------------------------------------------------------ markdown
_TAG = {"observed": "`OBSERVED`", "measured": "`MEASURED`", "ai": "`AI-SUGGESTED`", "verified": "`AI · VERIFIED`",
        "observed+measured": "`OBSERVED`/`MEASURED`", "observed:static": "`OBSERVED`",
        "observed:registry": "`OBSERVED`", "measured:execution": "`MEASURED`"}


def capsule_markdown(c: dict) -> str:
    d, r = c["dependency"], c["risk"]
    L = [f"# Dependency Exit Capsule: {d['name']}", "",
         f"Status: **{c.get('status', '').upper()}** · risk **{r['level']}** (score {r['score']}) · "
         f"target `{c['target'].get('source')}` @ `{(c['target'].get('commit') or '')[:10]}` · "
         f"Python {c['target'].get('python')}", "",
         "Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · "
         "`AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution", "",
         "## Dependency details " + _TAG["observed"], "",
         f"- Relation: {d['relation']}; installed {d['installed_version']}; imports {', '.join(d['import_names']) or '-'}"]
    for x in d["declared"]:
        L.append(f"- Declared in `{x['file']}:{x['line']}` as `{x['raw']}` ({x['group']})")
    reg = c.get("registry", {})
    if reg.get("available"):
        L.append(f"- PyPI latest {reg.get('latest_version')} ({reg.get('latest_release_date')}); "
                 f"upstream {reg.get('github') or 'n/a'}"
                 + (f", archived={reg.get('repo_archived')}, last push {reg.get('repo_last_push')}" if 'repo_archived' in reg else ""))
    L += ["", "## Risk indicators", "", "| Indicator | Severity | Evidence | Source |", "|---|---|---|---|"]
    for i in r["indicators"]:
        L.append(f"| {i['id']} | {i['severity']} | {_md(i['evidence'])} | {_TAG.get(i['provenance'], i['provenance'])} |")
    L += ["", "## Usage locations " + _TAG["observed"], ""]
    for u in c["usage_locations"]["items"] or [{"file": "-", "line": "-", "kind": "none", "code": "no usages found"}]:
        L.append(f"- `{u['file']}:{u['line']}` [{u['kind']}] `{_md(u['code'])}`")
    be = c["baseline_execution"]
    L += ["", "## Baseline execution " + _TAG["measured"], ""]
    for pr in be["import_probes"]:
        L.append(f"- `import {pr['module']}`: {'ok' if pr['ok'] else 'FAILS: ' + _md(pr['error'])}")
    for t in be["failing_tests"]:
        L.append(f"- Failing test `{t['test']}`: {_md(t['message'][:200])}")
    for w in be["warnings"]:
        L.append(f"- Warning ({w['run']}): `{w['file']}:{w['line']}` {w['cat']}: {_md(w['msg'][:160])}")
    if "proposed_replacement" in c:
        pr = c["proposed_replacement"]
        tag = _TAG[pr["provenance"]]
        target = pr.get("package") or pr.get("stdlib_module") or "-"
        L += ["", f"## Proposed replacement {tag}", "",
              f"**{pr['decision']}** → `{target}{pr.get('version_spec') or ''}` "
              f"(model confidence {pr.get('model_confidence')})", "", _md(pr.get("rationale") or ""), ""]
        for ch in pr.get("plan_checks") or []:
            L.append(f"- {'✓' if ch['passed'] else '✗'} {ch['check']} {_TAG['observed']} {ch['detail']}")
        ms = c["migration_steps"]
        L += ["", f"## Migration steps {_TAG[ms['provenance']]}", ""]
        L += [f"{n}. {_md(s)}" for n, s in enumerate(ms["steps"], 1)]
        L += ["", "Applied edits " + _TAG["measured"] + ":"]
        for e in ms["code_edits"]:
            L.append(f"- `{e['file']}`: {'applied' if e['applied'] else 'NOT applied'} ({e['reason']}) {_md(e.get('why', ''))}")
        for rc in ms["requirement_changes"]:
            ch = rc["change"]
            L.append(f"- {ch.get('action')} `{ch.get('requirement') or ch.get('package')}` in "
                     f"{', '.join(rc['files']) or 'no file (not applied)'}")
        L.append(f"\nFull patch: [`patch.diff`](patch.diff)")
        st = c["suggested_tests"]
        L += ["", f"## Suggested tests {_TAG['ai']}", ""]
        L += [f"- `{t['name']}`: {_md(t.get('purpose') or '')}" for t in st["tests"]] or ["- none"]
        ex = c["executed_test_results"]
        rt = ex["repository_tests"]
        L += ["", f"## Executed test results {_TAG['measured']}", "",
              f"- Install: {'ok' if ex['install'].get('ok') else 'FAILED'}; pip check {'ok' if ex['install'].get('pip_check_ok') else 'reports problems'}",
              f"- Repository tests: baseline {_counts(rt['baseline'])} → candidate {_counts(rt['candidate'])}",
              f"- Fixed: {', '.join(rt['fixed']) or 'none'}; regressions: {', '.join(rt['regressions']) or 'none'}",
              f"- Warnings attributed to this dependency: {ex['warnings_attributed_before']} before → {ex['warnings_attributed_after']} after"]
        for pr2 in ex["import_probes"]:
            L.append(f"- `import {pr2['module']}` in candidate: {'ok' if pr2['ok'] else 'FAILS: ' + _md(pr2['error'])}")
        if ex.get("risk_indicators_after_change"):
            L += ["", "| Risk indicator | Resolved by this change? | Re-checked on the changed copy |", "|---|---|---|"]
            for x in ex["risk_indicators_after_change"]:
                mark = {True: "yes", False: "**no**", None: "n/a"}[x["resolved"]]
                L.append(f"| {x['id']} | {mark} | {_md(x['detail'])} |")
        if ex.get("ai_written_tests"):
            L += ["", "| AI-written test | Original dependency | Replacement |", "|---|---|---|"]
            for row in ex["ai_written_tests"]["per_test"]:
                L.append(f"| `{row['test']}` | {row['original'] or '-'} | {row['replacement'] or '-'} |")
        L += ["", f"**Verdict: {ex['verdict'].upper()}** — {_md('; '.join(ex['verdict_reasons']))}"]
        L += ["", "## Compatibility gaps", ""]
        L += [f"- {_TAG[g['provenance']]} {_md(g['text'])}" for g in c["compatibility_gaps"]] or ["- none observed"]
        L += ["", "## Attempts", ""]
        L += [f"- #{a['attempt']} {a['model']} ({a['backend']}, {a['seconds']}s): {a['decision']} → {a['verdict']}"
              for a in c["attempts"]]
    L += ["", "## Open concerns and limitations", ""]
    L += [f"- {_TAG.get(o['provenance'], o['provenance'])} {_md(o['text'])}" for o in c.get("open_concerns", [])]
    return "\n".join(L) + "\n"


def _md(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _counts(c):
    if not c:
        return "n/a"
    return f"{c.get('passed', 0)} passed / {c.get('failed', 0) + c.get('error', 0)} failing"


# ------------------------------------------------------------------- writing
def write_all(out: Path, meta: dict, b, migrations: dict, combined: dict | None, ai_label: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    deps_dir = out / "capsules"
    deps_dir.mkdir(exist_ok=True)
    index = []
    caps = []
    for key, p in sorted(b.profiles.items(), key=lambda kv: -kv[1].score):
        mig = migrations.get(key)
        c = dependency_capsule(meta, b, p, mig)
        caps.append(c)
        d = deps_dir / slug(key)
        d.mkdir(exist_ok=True)
        (d / "capsule.json").write_text(json.dumps(c, indent=2, default=str), encoding="utf-8")
        (d / "CAPSULE.md").write_text(capsule_markdown(c), encoding="utf-8")
        if mig and mig.final:
            (d / "patch.diff").write_text(mig.final.diff, encoding="utf-8")
            if mig.final.plan:
                (d / "plan.json").write_text(json.dumps(mig.final.plan, indent=2), encoding="utf-8")
            if mig.final.ai_tests.get("code"):
                (d / "ai_tests.py").write_text(mig.final.ai_tests["code"], encoding="utf-8")
            for a in mig.attempts:
                (d / f"gemma-attempt-{a.number}.prompt.txt").write_text(a.exchange["prompt"], encoding="utf-8")
                (d / f"gemma-attempt-{a.number}.response.txt").write_text(a.exchange["raw_response"], encoding="utf-8")
        index.append({"dependency": p.name, "key": key, "level": p.level, "score": p.score,
                      "at_risk": p.at_risk, "status": c.get("status"),
                      "proposal": _proposal_text(c), "capsule": f"capsules/{slug(key)}/capsule.json"})
    summary = {
        "generated_at": _ts(), "generator": f"depexit {__version__}", "target": meta["target"],
        "ai": ai_label, "settings": meta.get("settings"),
        "baseline": {
            "install_ok": b.install_ok, "install_error": b.install_error, "pip_check": b.pip_check,
            "tests": b.tests.to_dict() if b.tests else None,
            "pyproject_install_path": {k: v for k, v in (b.alt or {}).items() if k != "log"} or None,
            "spec_conflicts": b.conflicts,
            "commented_out_requirements": [vars(x) for x in b.manifest.commented],
        },
        "dependencies": index,
        "combined_migration": {k: v for k, v in (combined or {}).items() if k != "diff"} or None,
        "limitations": LIMITATIONS,
        "execution_log": b.env.log,
    }
    (out / "capsule-index.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    if combined and combined.get("diff"):
        (out / "combined.patch").write_text(combined["diff"], encoding="utf-8")
    (out / "SUMMARY.md").write_text(summary_markdown(summary), encoding="utf-8")
    (out / "report.html").write_text(render_html(summary, caps), encoding="utf-8")
    return summary


def _proposal_text(c):
    pr = c.get("proposed_replacement")
    if not pr:
        return ""
    t = pr.get("package") or pr.get("stdlib_module") or ""
    return f"{pr.get('decision')} {t}{pr.get('version_spec') or ''}".strip()


def summary_markdown(s: dict) -> str:
    t = s["baseline"]["tests"] or {}
    L = [f"# DepExit run on `{s['target']['source']}`", "",
         f"Commit `{(s['target'].get('commit') or '')[:10]}` · Python {s['target'].get('python')} · AI: {s['ai']} · {s['generated_at']}", "",
         f"Baseline tests `MEASURED`: {_counts(t.get('counts'))}", "",
         "| Dependency | Risk | Score | Status | Proposal |", "|---|---|---|---|---|"]
    for d in s["dependencies"]:
        L.append(f"| [{d['dependency']}]({d['capsule'].replace('capsule.json', 'CAPSULE.md')}) | {d['level']} | "
                 f"{d['score']} | {d['status']} | {d['proposal'] or '-'} |")
    cm = s.get("combined_migration")
    if cm and cm.get("tests"):
        L += ["", f"All verified plans applied together `MEASURED`: {_counts(cm['tests']['counts'])} "
                  f"(patch: `combined.patch`)"]
    L += ["", "## Limitations", ""] + [f"- {x}" for x in s["limitations"]]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------- html
def render_html(s: dict, caps: list[dict]) -> str:
    from .report_html import page
    return page(s, caps)
