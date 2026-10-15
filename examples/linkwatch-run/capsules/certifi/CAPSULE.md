# Dependency Exit Capsule: certifi

Status: **VERIFIED** · risk **high** (score 20) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: undeclared; installed 2026.7.22; imports certifi
- PyPI latest 2026.7.22 (2026-07-22); upstream certifi/python-certifi

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| UNDECLARED | high | imported at linkwatch/checker.py:15, linkwatch/checker.py:4; only installed transitively | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/checker.py:4` [import] `import certifi`
- `linkwatch/checker.py:15` [reference] `return session.get(url, verify=certifi.where())`

## Baseline execution `MEASURED`

- `import certifi`: ok

## Proposed replacement `AI · VERIFIED`

**remove** → `-` (model confidence 1.0)

The 'certifi' package is used only to provide the CA bundle path to 'requests' via 'certifi.where()'. However, 'requests' uses 'certifi' by default when 'verify=True' (which is the default behavior). Removing the explicit call and import removes the undeclared dependency risk without changing functionality, as 'requests' already depends on 'certifi' and handles the bundle path internally.


## Migration steps `AI · VERIFIED`

1. Remove the explicit import of 'certifi' in 'linkwatch/checker.py'.
2. Remove the 'verify=certifi.where()' argument from the 'session.get' call in 'linkwatch/checker.py', allowing 'requests' to use its default CA bundle.

Applied edits `MEASURED`:
- `linkwatch/checker.py`: applied (exact match) Remove unused certifi import
- `linkwatch/checker.py`: applied (exact match) Use requests default CA bundle instead of explicitly calling certifi.where()

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_fetch_no_certifi_import`: Ensure that fetch still works and doesn't raise ImportError after removing certifi import

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import certifi` in candidate: ok

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_fetch_no_certifi_import` | passed | passed |

**Verdict: VERIFIED** — no regressions; every baseline problem attributed to this dependency is resolved

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` The code now relies on 'requests' default CA bundle management, which is the standard way to use 'certifi' with 'requests'.

## Attempts

- #1 gemma-4-31b-it (google, 169.2s): remove → verified

## Open concerns and limitations

- `AI-SUGGESTED` If the environment had a non-standard 'certifi' configuration that 'requests' doesn't pick up automatically, this could theoretically change behavior, but 'certifi.where()' is exactly what 'requests' uses internally.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
