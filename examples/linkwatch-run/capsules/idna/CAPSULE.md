# Dependency Exit Capsule: idna

Status: **VERIFIED** · risk **medium** (score 20) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 2.7; imports idna
- Declared in `requirements.txt:10` as `idna==2.7` (runtime)
- Declared in `pyproject.toml:22` as `idna==2.7` (runtime)
- PyPI latest 3.20 (2026-09-17); upstream kjd/idna

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| UNUSED | medium | no import, reference or CLI invocation found in code, Makefile, Dockerfile or CI files | `OBSERVED` |
| OUTDATED_PIN | medium | pinned 2.7 (2018-06-11), latest 3.20 | `OBSERVED` |

## Usage locations `OBSERVED`

- `-:-` [none] `no usages found`

## Baseline execution `MEASURED`

- `import idna`: ok

## Proposed replacement `AI · VERIFIED`

**remove** → `-` (model confidence 1.0)

The dependency 'idna' is marked as UNUSED (observed:static), meaning it is not imported or invoked anywhere in the codebase. It is likely a transitive dependency of 'requests' (which is declared in the project), and pinning it directly to an outdated version (2.7) is unnecessary and creates a security/maintenance risk.


## Migration steps `AI · VERIFIED`

1. Remove 'idna' from pyproject.toml
2. Remove 'idna' from requirements.txt

Applied edits `MEASURED`:
- remove `idna` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- none

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import idna` in candidate: ok

**Verdict: VERIFIED** — no regressions; every baseline problem attributed to this dependency is resolved

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` Removing the direct pin allows the package manager to resolve 'idna' to a version compatible with 'requests' (which requires idna >= 2.5, < 4), likely upgrading it to a 3.x version.

## Attempts

- #1 gemma-4-31b-it (google, 83.9s): remove → verified

## Open concerns and limitations

- `AI-SUGGESTED` If 'idna' is used via dynamic imports or an external plugin mechanism not detected by the AST scan, removing it from the direct dependencies might lead to a runtime ImportError if 'requests' is also removed or if the environment is strictly controlled.
- `OBSERVED` No AI-written tests were produced for this dependency.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
