"""Single-file HTML report. No external assets, works offline, light and dark."""
from __future__ import annotations

import json
from html import escape as e

CSS = """
:root{--bg:#f7f7f5;--panel:#fff;--ink:#17171a;--mute:#6b6b73;--line:#e4e4e0;--code:#f1f1ee;
--obs:#3b5bdb;--obs-bg:#edf1ff;--mea:#0b7a4b;--mea-bg:#e6f6ee;--ai:#9a5b00;--ai-bg:#fff3dc;--ver:#6741d9;--ver-bg:#f1ecff;
--crit:#c92a2a;--high:#e8590c;--med:#b08800;--low:#868e96;--ok:#2b8a3e}
@media (prefers-color-scheme:dark){:root{--bg:#111113;--panel:#19191c;--ink:#ececef;--mute:#9a9aa3;--line:#2a2a2f;--code:#212126;
--obs:#91a7ff;--obs-bg:#1d2340;--mea:#63e6be;--mea-bg:#10291f;--ai:#ffc078;--ai-bg:#33240f;--ver:#b197fc;--ver-bg:#251c3d;
--crit:#ff8787;--high:#ffa94d;--med:#ffd43b;--low:#adb5bd;--ok:#8ce99a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1080px;margin:0 auto;padding:40px 20px 80px}
h1{font-size:26px;letter-spacing:-.02em;margin:0 0 6px}h2{font-size:17px;margin:36px 0 12px;letter-spacing:-.01em}
h3{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:22px 0 8px;display:flex;gap:8px;align-items:center}
.meta{color:var(--mute);font-size:13px}code,.mono{font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
code{background:var(--code);padding:1px 5px;border-radius:4px}
a{color:var(--obs);text-decoration:none;font-weight:600}a:hover{text-decoration:underline}
.tag{display:inline-block;font:600 10.5px/1 ui-monospace,Menlo,monospace;letter-spacing:.04em;padding:4px 6px;border-radius:4px;white-space:nowrap;vertical-align:middle}
.t-observed{color:var(--obs);background:var(--obs-bg)}.t-measured{color:var(--mea);background:var(--mea-bg)}
.t-ai{color:var(--ai);background:var(--ai-bg)}.t-verified{color:var(--ver);background:var(--ver-bg)}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0 0;font-size:12.5px;color:var(--mute)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:24px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.stat b{display:block;font-size:24px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}.stat span{color:var(--mute);font-size:12.5px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);font-weight:600;background:var(--panel)}
tr:last-child td{border-bottom:0}
.lv{font-weight:600;font-size:12.5px}.lv-critical{color:var(--crit)}.lv-high{color:var(--high)}.lv-medium{color:var(--med)}.lv-low,.lv-none{color:var(--low)}
.st{font:600 11px/1 ui-monospace,Menlo,monospace;padding:4px 7px;border-radius:999px;border:1px solid currentColor;white-space:nowrap}
.st-verified{color:var(--ver)}.st-partial{color:var(--med)}.st-failed{color:var(--crit)}.st-not-required,.st-not-attempted{color:var(--low)}
.st-ai-unavailable,.st-no-usable-plan,.st-no-change{color:var(--high)}
details.dep{background:var(--panel);border:1px solid var(--line);border-radius:12px;margin:12px 0}
details.dep>summary{list-style:none;cursor:pointer;padding:14px 18px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
details.dep>summary::-webkit-details-marker{display:none}
details.dep>summary .name{font-weight:650;font-size:15px;min-width:140px}
details.dep>summary .prop{color:var(--mute);margin-left:auto;font-size:13px}
details.dep[open]>summary{border-bottom:1px solid var(--line)}
.body{padding:4px 18px 18px}
.box{border-radius:10px;padding:12px 14px;margin:8px 0;border:1px solid var(--line)}
.box.ai{border-color:var(--ai);background:var(--ai-bg)}.box.ver{border-color:var(--ver);background:var(--ver-bg)}
ul{margin:6px 0;padding-left:20px}li{margin:3px 0}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:6px 18px;font-size:13px}
.kv div span{color:var(--mute)}
.arrow{color:var(--mute);padding:0 6px}.pass{color:var(--ok);font-weight:600}.fail{color:var(--crit);font-weight:600}
pre{background:var(--code);padding:12px;border-radius:8px;overflow:auto;max-height:420px;margin:6px 0}
.small{font-size:12.5px;color:var(--mute)}
footer{margin-top:48px;color:var(--mute);font-size:12.5px}
@media (max-width:640px){main{padding:24px 14px 60px}details.dep>summary .prop{margin-left:0;width:100%}th:nth-child(3),td:nth-child(3){display:none}}
"""

TAGNAME = {"observed": "OBSERVED", "measured": "MEASURED", "ai": "AI-SUGGESTED", "verified": "AI · VERIFIED"}


def tag(prov: str) -> str:
    p = prov.split(":")[0].split("+")[0]
    return f'<span class="tag t-{p}">{TAGNAME.get(p, p.upper())}</span>'


def counts(c) -> str:
    if not c:
        return "n/a"
    bad = c.get("failed", 0) + c.get("error", 0)
    cls = "fail" if bad else "pass"
    return f'<span class="{cls}">{c.get("passed", 0)} passed · {bad} failing</span>'


def outcome(o) -> str:
    if o is None:
        return '<span class="small">–</span>'
    return f'<span class="{"pass" if o == "passed" else "fail"}">{e(o)}</span>'


def dep_section(c: dict) -> str:
    d, r = c["dependency"], c["risk"]
    status = c.get("status", "")
    pr = c.get("proposed_replacement")
    prop = ""
    if pr:
        prop = f"{e(pr['decision'] or '')} → <code>{e((pr.get('package') or pr.get('stdlib_module') or '-') + (pr.get('version_spec') or ''))}</code>"
    h = [f'<details class="dep" id="{e(d["key"])}"{" open" if status in ("verified", "partial", "failed") else ""}>',
         f'<summary><span class="name">{e(d["name"])}</span><span class="lv lv-{r["level"]}">{r["level"]} · {r["score"]}</span>'
         f'<span class="st st-{e(status)}">{e(status)}</span><span class="prop">{prop}</span></summary><div class="body">']
    reg = c.get("registry", {})
    h.append(f'<h3>Dependency details {tag("observed")}</h3><div class="kv">'
             f'<div><span>Relation</span> {e(d["relation"])}</div>'
             f'<div><span>Installed</span> <code>{e(str(d["installed_version"]))}</code></div>'
             f'<div><span>Latest on PyPI</span> <code>{e(str(reg.get("latest_version")))}</code> ({e(str(reg.get("latest_release_date")))})</div>'
             f'<div><span>Upstream</span> {e(str(reg.get("github") or "n/a"))}'
             + (f' · archived: {e(str(reg.get("repo_archived")))}' if "repo_archived" in reg else "") + '</div></div>')
    if d["declared"]:
        h.append("<ul>" + "".join(f'<li><code>{e(x["file"])}:{x["line"]}</code> <code>{e(x["raw"])}</code> ({e(x["group"])})</li>'
                                  for x in d["declared"]) + "</ul>")
    h.append('<h3>Risk indicators</h3><table><tr><th>Indicator</th><th>Severity</th><th>Evidence</th><th>Source</th></tr>')
    for i in r["indicators"]:
        h.append(f'<tr><td><b>{e(i["id"])}</b><div class="small">{e(i["title"])}</div></td>'
                 f'<td class="lv lv-{i["severity"]}">{i["severity"]}</td><td class="mono">{e(i["evidence"])}</td><td>{tag(i["provenance"])}</td></tr>')
    if not r["indicators"]:
        h.append('<tr><td colspan="4" class="small">No risk indicators.</td></tr>')
    h.append("</table>")
    us = c["usage_locations"]["items"]
    h.append(f'<h3>Usage locations {tag("observed")}</h3>')
    h.append("<ul>" + ("".join(f'<li><code>{e(u["file"])}:{u["line"]}</code> <span class="small">{e(u["kind"])}</span> '
                               f'<span class="mono">{e(u["code"])}</span></li>' for u in us) or "<li class='small'>No usages found.</li>") + "</ul>")
    be = c["baseline_execution"]
    if be["import_probes"] or be["failing_tests"] or be["warnings"]:
        h.append(f'<h3>Baseline execution {tag("measured")}</h3><ul>')
        for p in be["import_probes"]:
            h.append(f'<li><code>import {e(p["module"])}</code> {"<span class=pass>ok</span>" if p["ok"] else "<span class=fail>fails</span> <span class=mono>" + e(p["error"]) + "</span>"}</li>')
        for t in be["failing_tests"]:
            h.append(f'<li><span class="fail">failing</span> <code>{e(t["test"])}</code> <span class="mono">{e(t["message"][:220])}</span></li>')
        for w in be["warnings"]:
            h.append(f'<li>{e(w["cat"])} ({e(w["run"])}): <code>{e(w["file"])}:{w["line"]}</code> <span class="mono">{e(w["msg"][:200])}</span></li>')
        h.append("</ul>")
    if pr:
        ver = pr["provenance"] == "verified"
        h.append(f'<h3>Proposed replacement {tag(pr["provenance"])}</h3><div class="box {"ver" if ver else "ai"}">'
                 f'<div><b>{prop}</b> <span class="small">model confidence {e(str(pr.get("model_confidence")))}</span></div>'
                 f'<p>{e(pr.get("rationale") or "")}</p>')
        if pr.get("plan_checks"):
            h.append("<ul>" + "".join(f'<li>{"✓" if x["passed"] else "✗"} {e(x["check"])} {tag("observed")} <span class="small">{e(x["detail"])}</span></li>'
                                      for x in pr["plan_checks"]) + "</ul>")
        ms = c["migration_steps"]
        h.append(f'</div><h3>Migration steps {tag(ms["provenance"])}</h3><ol>' +
                 "".join(f"<li>{e(s)}</li>" for s in ms["steps"]) + "</ol>")
        h.append(f'<h3>Applied changes {tag("measured")}</h3><ul>')
        for x in ms["code_edits"]:
            h.append(f'<li><code>{e(x["file"])}</code> {"<span class=pass>applied</span>" if x["applied"] else "<span class=fail>not applied</span>"} '
                     f'<span class="small">{e(x["reason"])} · {e(x.get("why") or "")}</span></li>')
        for x in ms["requirement_changes"]:
            ch = x["change"]
            h.append(f'<li>{e(ch.get("action", ""))} <code>{e(ch.get("requirement") or ch.get("package") or "")}</code> '
                     f'<span class="small">in {e(", ".join(x["files"]) or "no file")}</span></li>')
        h.append("</ul>")
        ex = c["executed_test_results"]
        rt = ex["repository_tests"]
        h.append(f'<h3>Executed test results {tag("measured")}</h3><div class="kv">'
                 f'<div><span>Install</span> {"<span class=pass>ok</span>" if ex["install"].get("ok") else "<span class=fail>failed</span>"}'
                 f' · pip check {"<span class=pass>ok</span>" if ex["install"].get("pip_check_ok") else "<span class=fail>problems</span>"}</div>'
                 f'<div><span>Repo tests</span> {counts(rt["baseline"])}<span class="arrow">→</span>{counts(rt["candidate"])}</div>'
                 f'<div><span>Warnings for this dep</span> {ex["warnings_attributed_before"]}<span class="arrow">→</span>{ex["warnings_attributed_after"]}</div>'
                 f'<div><span>Fixed</span> {e(", ".join(t.split("::")[-1] for t in rt["fixed"]) or "none")} · '
                 f'<span>Regressions</span> {e(", ".join(rt["regressions"]) or "none")}</div></div>')
        if ex.get("risk_indicators_after_change"):
            h.append(f'<p class="small">Each risk re-checked on the changed copy {tag("measured")}</p>'
                     '<table><tr><th>Risk indicator</th><th>Resolved?</th><th>Re-check</th></tr>' +
                     "".join(f'<tr><td><b>{e(x["id"])}</b></td><td>{ {True: "<span class=pass>yes</span>", False: "<span class=fail>no</span>", None: "<span class=small>n/a</span>"}[x["resolved"]] }</td>'
                             f'<td class="mono">{e(x["detail"])}</td></tr>' for x in ex["risk_indicators_after_change"]) + "</table>")
        if ex.get("ai_written_tests"):
            h.append(f'<p class="small">AI-written tests {tag("ai")} executed against both dependency sets {tag("measured")}</p>'
                     '<table><tr><th>Test</th><th>Original dependency</th><th>Replacement</th></tr>' +
                     "".join(f'<tr><td><code>{e(x["test"])}</code></td><td>{outcome(x["original"])}</td><td>{outcome(x["replacement"])}</td></tr>'
                             for x in ex["ai_written_tests"]["per_test"]) + "</table>")
        v = ex["verdict"]
        h.append(f'<div class="box {"ver" if v == "verified" else ""}"><b>Verdict: <span class="st st-{e(v)}">{e(v)}</span></b> '
                 f'{e("; ".join(ex["verdict_reasons"]))}</div>')
        if c.get("compatibility_gaps"):
            h.append('<h3>Compatibility gaps</h3><ul>' + "".join(f'<li>{tag(g["provenance"])} {e(g["text"])}</li>' for g in c["compatibility_gaps"]) + "</ul>")
        h.append('<h3>Attempts</h3><ul>' + "".join(
            f'<li>#{a["attempt"]} <code>{e(str(a["model"]))}</code> via {e(str(a["backend"]))}, {a["seconds"]}s: '
            f'{e(str(a["decision"]))} → <span class="st st-{e(a["verdict"])}">{e(a["verdict"])}</span></li>' for a in c["attempts"]) + "</ul>")
    if c.get("open_concerns"):
        h.append('<h3>Open concerns and limitations</h3><ul>' + "".join(
            f'<li>{tag(o["provenance"])} {e(o["text"])}</li>' for o in c["open_concerns"]) + "</ul>")
    h.append(f'<p class="small">Files: <code>capsules/{e(d["key"])}/capsule.json</code>, <code>CAPSULE.md</code>'
             + (', <code>patch.diff</code>, <code>plan.json</code>, Gemma prompt/response transcripts' if pr else "") + "</p>")
    h.append("</div></details>")
    return "".join(h)


def page(s: dict, caps: list[dict]) -> str:
    deps = s["dependencies"]
    t = (s["baseline"]["tests"] or {}).get("counts") or {}
    at_risk = sum(1 for d in deps if d["at_risk"])
    verified = sum(1 for d in deps if d["status"] == "verified")
    attempted = sum(1 for d in deps if d["status"] in ("verified", "partial", "failed"))
    cm = s.get("combined_migration") or {}
    ct = (cm.get("tests") or {}).get("counts")
    tgt = s["target"]
    rows = "".join(
        f'<tr><td><a href="#{e(d["key"])}">{e(d["dependency"])}</a></td><td class="lv lv-{d["level"]}">{d["level"]}</td>'
        f'<td>{d["score"]}</td><td><span class="st st-{e(d["status"])}">{e(d["status"])}</span></td>'
        f'<td class="mono">{e(d["proposal"] or "–")}</td></tr>' for d in deps)
    conflicts = "".join(
        f'<li><b>{e(c["package"])}</b>: ' + ", ".join(f'<code>{e(x["file"])}:{x["line"]} {e(x["spec"])}</code>' for x in c["declarations"]) + "</li>"
        for c in s["baseline"]["spec_conflicts"])
    alt = s["baseline"].get("pyproject_install_path") or {}
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DepExit Report</title><style>{CSS}</style></head><body><main>
<h1>Dependency Exit Report</h1>
<div class="meta"><code>{e(tgt.get("source", ""))}</code> @ <code>{e((tgt.get("commit") or "")[:10])}</code> · Python {e(str(tgt.get("python")))} · AI: {e(s["ai"])} · {e(s["generated_at"])}</div>
<div class="legend"><span>{tag("observed")} read from files or registries</span><span>{tag("measured")} produced by execution</span>
<span>{tag("ai")} Gemma proposal, unverified</span><span>{tag("verified")} Gemma proposal confirmed by execution</span></div>
<div class="stats">
<div class="stat"><b>{counts(t)}</b><span>baseline test suite {tag("measured")}</span></div>
<div class="stat"><b>{at_risk} / {len(deps)}</b><span>dependencies at risk {tag("observed")}</span></div>
<div class="stat"><b>{verified} / {attempted}</b><span>{"migrations verified by execution" if s["ai"] != "off" else "migrations verified (AI was off for this run)"}</span></div>
<div class="stat"><b>{counts(ct) if ct else "–"}</b><span>all verified plans applied together</span></div>
</div>
<h2>Dependencies</h2>
<table><tr><th>Dependency</th><th>Risk</th><th>Score</th><th>Status</th><th>Proposal</th></tr>{rows}</table>
{f'<h2>Manifest conflicts {tag("observed")}</h2><ul>{conflicts}</ul>' if conflicts else ""}
{f'<p class="small">Installing via <code>pyproject.toml</code> instead of requirements files {tag("measured")}: tests {counts((alt.get("tests") or {}).get("counts"))}</p>' if alt else ""}
<h2>Capsules</h2>
{"".join(dep_section(c) for c in caps)}
<h2>Limitations</h2><ul>{"".join(f"<li>{e(x)}</li>" for x in s["limitations"])}</ul>
<footer>Generated by {e(s["generator"])}. Machine-readable data: <code>capsule-index.json</code> and <code>capsules/*/capsule.json</code>.</footer>
</main></body></html>"""
