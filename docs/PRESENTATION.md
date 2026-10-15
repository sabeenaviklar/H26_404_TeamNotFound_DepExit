# Slide content for the organizer template

Paste each block into the matching slide of the official template. Numbers marked ⟨run⟩ should be copied from your own final `capsule-out/SUMMARY.md` so they match what you demo.

---

## Slide 1 · Team Information & Track

**Team:** 404_TeamNotFound · ⟨member names⟩
**Track 1:** Gemma 4 · Dependency Resilience
**Project:** DepExit, an evidence-first dependency exit planner

**Problem.** Maintainers learn that a dependency has rotted only when something breaks. LinkWatch shows how quietly it happens: installed exactly as its README says on Python 3.12, one test already fails, `make test-nose` crashes, and the two install paths disagree on the pydantic major version. AI can suggest fixes, but a suggestion is not evidence, and a wrong migration can break otherwise healthy software.

---

## Slide 2 · Solution & Workflow

**Solution.** Deterministic code observes and measures, Gemma 4 proposes, and execution decides.

Workflow (use the Mermaid diagram from the README, or redraw it as five boxes):
1. **Inventory**: manifests, AST usage scan, Makefile/CI references
2. **Baseline**: fresh venv, install, import probes, test suite, warnings, PyPI and GitHub history
3. **Risk engine**: indicators with evidence, then at-risk dependencies are selected
4. **Gemma 4**: replacement, code edits, requirement changes, characterisation tests
5. **Verifier**: apply to a copy, reinstall, run the repo tests plus the AI tests against both the original and the replacement, compare with the baseline; on failure, feed the evidence back to Gemma once

**Data sources:** the target repo itself, the PyPI JSON API, the GitHub REST API.
**Outputs:** one Dependency Exit Capsule per dependency (JSON + Markdown + patch), an HTML report, and a combined patch of all verified migrations.
**Verification:** every field is tagged OBSERVED, MEASURED, AI-SUGGESTED or AI · VERIFIED.

---

## Slide 3 · Technical Approach

- **Stack:** Python 3.11+ standard library only (`ast`, `tomllib`, `venv`, `subprocess`, `urllib`); pytest with JUnit XML; uv or pip for isolated environments.
- **Model:** Gemma 4 `gemma-4-31b-it` through the Gemini API (free AI Studio key), or a local Gemma 4 through Ollama. Temperature 0.2, strict JSON reply.
- **Attribution:** a failing test is blamed on the innermost third-party frame plus the module named in the exception, so Jinja2 and MarkupSafe are blamed and Click, which only passed the call through, is not.
- **Hallucination guards:** proposed packages must exist on PyPI, edits must match the real file text, and paths cannot escape the repo.
- **Verdict rules:** `verified` requires no regressions, every attributed failure and warning gone, the replacement importing, no leftover references, and the AI tests passing on the replacement.
- **Testing of the tool itself:** unit tests in `depexit_tests/`, plus end-to-end runs on LinkWatch with both uv and pip.

---

## Slide 4 · Feasibility & Viability

- **Resources:** a laptop, Python 3.12, a free Gemini API key. No paid APIs, no cloud services, no GPU. A full run on LinkWatch takes about ⟨run⟩ minutes.
- **Challenges:** free-tier rate limits (handled with backoff), model variance between runs (handled by verification, not trust), tests that don't cover every code path (disclosed in every capsule).
- **Limitations:** Python only; requirements.txt and PEP 621 pyproject; each dependency verified in isolation plus one combined run.
- **Scalability:** stdlib-only and repository-agnostic. It works on any Python repo with a test suite, and `--only` / `--max-deps` keep big repos tractable.
- **Sustainability:** capsules are plain files that live in the repo. `depexit replay` re-verifies a saved plan on a newer commit **without calling the model**, so evidence stays reproducible.

---

## Slide 5 · Impact & Benefits

- **Users:** open-source maintainers, small teams inheriting old Python projects, reviewers who need to approve dependency bumps.
- **Benefit:** a migration arrives with its evidence. The reviewer sees what was observed, what was measured, what the AI suggested, and what was proven, instead of a bare diff.
- **Measured on LinkWatch** ⟨run⟩: baseline 9/10 tests passing → ⟨X⟩/⟨Y⟩ with all verified plans applied; ⟨N⟩ at-risk dependencies found, ⟨V⟩ migrations verified; Python 3.12 test runner restored (nose removed).
- **Long term:** fewer surprise breakages, safer upgrades, and a reusable record of why each dependency was replaced.

---

## Slide 6 · Research & References

- Gemma 4 on the Gemini API: https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api
- Gemma license and terms: https://ai.google.dev/gemma/terms
- PyPI JSON API: https://docs.pypi.org/api/json/
- GitHub REST API, repositories: https://docs.github.com/en/rest/repos/repos
- PEP 503 (name normalisation): https://peps.python.org/pep-0503/
- PEP 621 (pyproject metadata): https://peps.python.org/pep-0621/
- Python 3.12 removal of `imp` (breaks nose): https://docs.python.org/3/whatsnew/3.12.html
- pkg_resources deprecation: https://setuptools.pypa.io/en/latest/pkg_resources.html
- MarkupSafe 2.1 changelog (`soft_unicode` removed): https://markupsafe.palletsprojects.com/en/stable/changes/
- Pydantic V1 → V2 migration guide: https://docs.pydantic.dev/latest/migration/
- Existing tools and how DepExit differs: Dependabot and Renovate bump versions but don't explain risk or prove behaviour; `pip-audit` covers vulnerabilities (out of scope here); `deptry` finds unused or undeclared dependencies statically. DepExit combines static, registry and execution evidence and verifies AI-written migrations.

---

## Demo script (3 minutes)

1. `python -m depexit doctor`: show the live Gemma call works.
2. `python -m depexit analyze https://github.com/rishrek/LinkWatch --only jinja2,nose,pydantic`: narrate the risk ranking, then each plan → VERIFIED.
3. Open `report.html`: show the four provenance tags, Jinja2's AI test failing on the original and passing on the replacement, and the combined run.
4. Open `capsules/jinja2/gemma-attempt-1.response.txt`: the raw model output, kept as evidence.
5. `python -m depexit replay capsule-out/capsules/jinja2/capsule.json`: re-verified with no model call.

Keep a screen recording of steps 1 to 3 as the fallback.
