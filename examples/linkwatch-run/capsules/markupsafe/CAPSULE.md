# Dependency Exit Capsule: MarkupSafe

Status: **VERIFIED** · risk **critical** (score 60) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: transitive; installed 3.0.4; imports markupsafe
- PyPI latest 3.0.4 (2026-10-02); upstream pallets/markupsafe

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| TEST_FAILURES | critical | tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py) | `MEASURED` |
| TRANSITIVE_BREAKAGE | high | resolved to 3.0.4, appears in failing traceback(s) | `MEASURED` |

## Usage locations `OBSERVED`

- `-:-` [none] `no usages found`

## Baseline execution `MEASURED`

- `import markupsafe`: ok
- Failing test `tests/test_report.py::test_report_renders_all_sites`: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)

## Proposed replacement `AI · VERIFIED`

**upgrade** → `Jinja2==3.1.4` (model confidence 0.9)

The failure 'ImportError: cannot import name 'soft_unicode' from 'markupsafe'' is a known incompatibility between Jinja2 < 3.0 and MarkupSafe >= 2.1.0. MarkupSafe removed 'soft_unicode' in version 2.1.0. Since the project is pinned to Jinja2 2.11.3 and the environment has resolved MarkupSafe to 3.0.4, the tests fail. To resolve this on Python 3.12, we must upgrade Jinja2 to 3.1.4, as pinning MarkupSafe to a version < 2.1.0 (which still provides 'soft_unicode') would likely cause installation failures on Python 3.12 due to C API incompatibilities.

- ✓ package 'Jinja2' exists on PyPI `OBSERVED` latest 3.1.6

## Migration steps `AI · VERIFIED`

1. Upgrade Jinja2 from 2.11.3 to 3.1.4 in pyproject.toml and requirements.txt to ensure compatibility with the installed version of MarkupSafe (3.0.4).

Applied edits `MEASURED`:
- set `Jinja2==3.1.4` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_jinja2_markupsafe_compatibility`: Verify that Jinja2 can render a template and MarkupSafe is functional without relying on soft_unicode

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 10 passed / 0 failing
- Fixed: tests/test_report.py::test_report_renders_all_sites; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import jinja2` in candidate: ok
- `import markupsafe` in candidate: ok

| Risk indicator | Resolved by this change? | Re-checked on the changed copy |
|---|---|---|
| TEST_FAILURES | yes | attributed failures now pass |
| TRANSITIVE_BREAKAGE | yes | attributed failures now pass |

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_jinja2_markupsafe_compatibility` | error (module failed to import) | passed |

**Verdict: VERIFIED** — no regressions; resolved TEST_FAILURES, TRANSITIVE_BREAKAGE

## Compatibility gaps

- `MEASURED` Behaviour differs: test_jinja2_markupsafe_compatibility error (module failed to import) on the original dependency but passes on the replacement (expected when the original is broken)
- `AI-SUGGESTED` Upgrading Jinja2 from 2.11 to 3.1 is generally backward compatible for basic template rendering, but some internal APIs may have changed.

## Attempts

- #1 gemma-4-31b-it (google, 293.5s): upgrade → verified

## Open concerns and limitations

- `AI-SUGGESTED` Potential breaking changes in Jinja2 3.x templates, although unlikely for the simple HTML reports used in this project.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
