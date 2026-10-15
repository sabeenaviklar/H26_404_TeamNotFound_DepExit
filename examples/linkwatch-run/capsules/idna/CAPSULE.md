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

The dependency 'idna' is marked as UNUSED by both static analysis and AST scan, meaning it is not imported or invoked anywhere in the repository's code. It is a transitive dependency of 'requests' (which is declared in the project), so removing the direct pin allows 'requests' to manage its own compatible version of 'idna', reducing maintenance overhead and removing an outdated pin (2.7).


## Migration steps `AI · VERIFIED`

1. Remove 'idna' from pyproject.toml and requirements.txt

Applied edits `MEASURED`:
- remove `idna` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_requests_idna_resolution`: Ensure requests still functions for domain-based URLs after removing direct idna pin

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import idna` in candidate: ok

| Risk indicator | Resolved by this change? | Re-checked on the changed copy |
|---|---|---|
| UNUSED | yes | removed from manifests |
| OUTDATED_PIN | yes | now 3.20 |

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_requests_request_init` | passed | passed |

**Verdict: VERIFIED** — no regressions; resolved UNUSED, OUTDATED_PIN

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` Removing the pin allows the environment to install a newer version of idna (e.g., 3.x) as required by requests, which is more compatible with Python 3.12.

## Attempts

- #1 gemma-4-31b-it (google, 124.8s): remove → verified

## Open concerns and limitations

- `AI-SUGGESTED` If there was a very specific, undocumented reliance on idna 2.7 behavior that static analysis missed, it could cause issues, though this is unlikely for a library like idna.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
