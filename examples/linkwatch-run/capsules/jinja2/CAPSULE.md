# Dependency Exit Capsule: Jinja2

Status: **VERIFIED** · risk **critical** (score 90) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 2.11.3; imports jinja2
- Declared in `requirements.txt:4` as `Jinja2==2.11.3` (runtime)
- Declared in `pyproject.toml:16` as `Jinja2==2.11.3` (runtime)
- PyPI latest 3.1.6 (2025-03-05); upstream pallets/jinja

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| IMPORT_FAILS | critical | ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py) | `MEASURED` |
| TEST_FAILURES | critical | tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py) | `MEASURED` |
| OUTDATED_PIN | medium | pinned 2.11.3 (2021-01-31), latest 3.1.6 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/report.py:3` [from-import] `from jinja2 import Environment, FileSystemLoader, select_autoescape`
- `linkwatch/report.py:9` [reference] `return Environment(`
- `linkwatch/report.py:10` [reference] `loader=FileSystemLoader(template_dir()),`
- `linkwatch/report.py:11` [reference] `autoescape=select_autoescape(["html", "j2"]),`

## Baseline execution `MEASURED`

- `import jinja2`: FAILS: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- Failing test `tests/test_report.py::test_report_renders_all_sites`: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)

## Proposed replacement `AI · VERIFIED`

**upgrade** → `Jinja2>=3.1.0` (model confidence 1.0)

The current version of Jinja2 (2.11.3) is incompatible with newer versions of MarkupSafe, leading to IMPORT_FAILS and TEST_FAILURES (ImportError: cannot import name 'soft_unicode' from 'markupsafe'). Upgrading to Jinja2 3.x resolves this issue and provides support for Python 3.12.

- ✓ package 'Jinja2' exists on PyPI `OBSERVED` latest 3.1.6

## Migration steps `AI · VERIFIED`

1. Upgrade Jinja2 to >=3.1.0 in pyproject.toml and requirements.txt

Applied edits `MEASURED`:
- set `Jinja2>=3.1.0` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_jinja2_import`: Verify that jinja2 and its required components can be imported without the soft_unicode error

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 10 passed / 0 failing
- Fixed: tests/test_report.py::test_report_renders_all_sites; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import jinja2` in candidate: ok

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_jinja2_import` | error (module failed to import) | passed |

**Verdict: VERIFIED** — no regressions; every baseline problem attributed to this dependency is resolved

## Compatibility gaps

- `MEASURED` Behaviour differs: test_jinja2_import error (module failed to import) on the original dependency but passes on the replacement (expected when the original is broken)
- `AI-SUGGESTED` Jinja2 3.x is generally backward compatible with 2.x for the features used in this project (Environment, FileSystemLoader, select_autoescape).

## Attempts

- #1 gemma-4-31b-it (google, 92.4s): upgrade → verified

## Open concerns and limitations

- `AI-SUGGESTED` Potential changes in template rendering behavior between Jinja2 2.11 and 3.1, although unlikely for basic usage.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
