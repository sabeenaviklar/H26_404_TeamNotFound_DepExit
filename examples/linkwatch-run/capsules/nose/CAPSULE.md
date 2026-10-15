# Dependency Exit Capsule: nose

Status: **VERIFIED** · risk **critical** (score 66) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 1.3.7; imports nose
- Declared in `requirements-dev.txt:2` as `nose==1.3.7` (dev)
- PyPI latest 1.3.7 (2015-06-02); upstream n/a

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| IMPORT_FAILS | critical | ModuleNotFoundError: No module named 'imp' | `MEASURED` |
| TOOLING_ONLY | low | Makefile:14 `nosetests tests/` | `OBSERVED` |
| STALE_UPSTREAM | high | latest 1.3.7 released 2015-06-02 | `OBSERVED` |
| OLD_PIN | low | 1.3.7 released 2015-06-02, latest 1.3.7 | `OBSERVED` |

## Usage locations `OBSERVED`

- `Makefile:14` [text] `nosetests tests/`

## Baseline execution `MEASURED`

- `import nose`: FAILS: ModuleNotFoundError: No module named 'imp'

## Proposed replacement `AI · VERIFIED`

**remove** → `-` (model confidence 1.0)

The 'nose' package is broken on Python 3.12 because it relies on the 'imp' module, which was removed in this Python version (IMPORT_FAILS). Furthermore, 'nose' is unmaintained (STALE_UPSTREAM) and redundant since 'pytest' is already a declared dependency and used as the primary test runner in the Makefile.


## Migration steps `AI · VERIFIED`

1. Remove 'nose' from requirements-dev.txt
2. Remove the 'test-nose' target from the Makefile

Applied edits `MEASURED`:
- `Makefile`: applied (exact match) Remove test-nose from phony targets
- `Makefile`: applied (exact match) Remove the broken and redundant nose test target
- remove `nose` in requirements-dev.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- none

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after

| Risk indicator | Resolved by this change? | Re-checked on the changed copy |
|---|---|---|
| IMPORT_FAILS | yes | imports cleanly |
| TOOLING_ONLY | n/a | informational |
| STALE_UPSTREAM | yes | package no longer used |
| OLD_PIN | yes | package no longer used |

**Verdict: VERIFIED** — no regressions; resolved IMPORT_FAILS, STALE_UPSTREAM, OLD_PIN

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` The project already uses pytest for its main 'test' target, so removing nose does not affect the primary testing workflow.

## Attempts

- #1 gemma-4-31b-it (google, 145.7s): remove → verified

## Open concerns and limitations

- `OBSERVED` No AI-written tests were produced for this dependency.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
