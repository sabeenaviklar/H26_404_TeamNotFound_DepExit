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

**upgrade** → `Jinja2>=3.1.2` (model confidence 1.0)

The observed 'ImportError: cannot import name 'soft_unicode' from 'markupsafe'' is a known incompatibility between Jinja2 versions prior to 3.0 and MarkupSafe versions 2.1.0 and later. The repository is currently pinned to Jinja2 2.11.3, while the environment has MarkupSafe 3.0.4. Upgrading Jinja2 to >= 3.1.2 resolves this issue and ensures compatibility with Python 3.12.

- ✓ package 'Jinja2' exists on PyPI `OBSERVED` latest 3.1.6

## Migration steps `AI · VERIFIED`

1. Upgrade Jinja2 to >= 3.1.2 in pyproject.toml and requirements.txt to resolve the incompatibility with MarkupSafe 3.0.4.

Applied edits `MEASURED`:
- `pyproject.toml`: applied (exact match) Upgrade Jinja2 to a version compatible with MarkupSafe 3.0.4 and Python 3.12.
- `requirements.txt`: applied (exact match) Upgrade Jinja2 to a version compatible with MarkupSafe 3.0.4 and Python 3.12.
- set `Jinja2>=3.1.2` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_jinja2_basic_rendering`: Verify that Jinja2 still renders basic templates correctly after the upgrade.

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 10 passed / 0 failing
- Fixed: tests/test_report.py::test_report_renders_all_sites; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import jinja2` in candidate: ok
- `import markupsafe` in candidate: ok

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_jinja2_basic_rendering` | error (module failed to import) | passed |

**Verdict: VERIFIED** — no regressions; every baseline problem attributed to this dependency is resolved

## Compatibility gaps

- `MEASURED` Behaviour differs: test_jinja2_basic_rendering error (module failed to import) on the original dependency but passes on the replacement (expected when the original is broken)
- `AI-SUGGESTED` Jinja2 3.x is generally backward compatible with 2.x for basic template rendering, which is the primary use case in this repository.

## Attempts

- #1 gemma-4-31b-it (google, 557.8s): upgrade → verified

## Open concerns and limitations

- `AI-SUGGESTED` While basic rendering is stable, any advanced Jinja2 2.11 specific internal APIs used by the project (though none were found in the AST scan) might have changed in 3.x.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
