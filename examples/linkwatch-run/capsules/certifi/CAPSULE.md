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

The `certifi` package is used only to provide the CA bundle path to `requests.get()` via `verify=certifi.where()`. However, `requests` already uses `certifi` by default when `verify=True` (which is the default value). Removing the explicit import and call removes the redundant code and resolves the UNDECLARED dependency risk without changing the behavior of the application.


## Migration steps `AI · VERIFIED`

1. Remove the explicit import of `certifi` in `linkwatch/checker.py`.
2. Remove the `verify=certifi.where()` argument from the `session.get` call in `linkwatch/checker.py`, allowing `requests` to use its default verification behavior.

Applied edits `MEASURED`:
- `linkwatch/checker.py`: applied (exact match) Remove unused import
- `linkwatch/checker.py`: applied (exact match) requests uses certifi by default for SSL verification

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_fetch_basic`: Ensure fetch still works for basic HTTP requests after removing explicit certifi usage

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import certifi` in candidate: ok

| Risk indicator | Resolved by this change? | Re-checked on the changed copy |
|---|---|---|
| UNDECLARED | yes | no longer imported |

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_fetch_basic` | passed | passed |

**Verdict: VERIFIED** — no regressions; resolved UNDECLARED

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` The application will now respect the `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` environment variables if set, which is the standard behavior for `requests` and generally preferred over forcing the `certifi` bundle.

## Attempts

- #1 gemma-4-31b-it (google, 147.9s): remove → verified

## Open concerns and limitations

- `AI-SUGGESTED` If the environment has a broken `certifi` installation that `requests` cannot find but `certifi.where()` could somehow resolve, this might fail, but this is extremely unlikely as `requests` depends on `certifi`.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
