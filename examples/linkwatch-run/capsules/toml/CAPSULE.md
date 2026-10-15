# Dependency Exit Capsule: toml

Status: **VERIFIED** · risk **high** (score 23) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 0.10.2; imports toml
- Declared in `requirements.txt:1` as `toml==0.10.2` (runtime)
- Declared in `pyproject.toml:13` as `toml==0.10.2` (runtime)
- PyPI latest 0.10.2 (2020-11-01); upstream uiri/toml

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| STALE_UPSTREAM | high | latest 0.10.2 released 2020-11-01 | `OBSERVED` |
| OLD_PIN | low | 0.10.2 released 2020-11-01, latest 0.10.2 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/config.py:3` [import] `import toml`
- `linkwatch/config.py:37` [reference] `data = toml.load(path)`

## Baseline execution `MEASURED`

- `import toml`: ok

## Proposed replacement `AI · VERIFIED`

**replace** → `tomllib` (model confidence 1.0)

The 'toml' package is stale (STALE_UPSTREAM, no release in 5 years). Since the target Python version is 3.12.14, we can use the standard library 'tomllib' module introduced in Python 3.11, which is the preferred approach.

- ✓ 'tomllib' is a standard-library module `OBSERVED` 

## Migration steps `AI · VERIFIED`

1. Update 'requires-python' in 'pyproject.toml' to '>=3.11' to support 'tomllib'.
2. Replace 'import toml' with 'import tomllib' in 'linkwatch/config.py'.
3. Update 'toml.load(path)' to use 'tomllib.load()' with a binary file handle, as 'tomllib' requires binary mode.
4. Remove 'toml' from 'requirements.txt' and 'pyproject.toml'.

Applied edits `MEASURED`:
- `linkwatch/config.py`: applied (exact match) Replace stale toml package with standard library tomllib.
- `linkwatch/config.py`: applied (exact match) tomllib.load requires a binary file-like object, unlike toml.load which accepts a path string.
- `pyproject.toml`: applied (exact match) tomllib was introduced in Python 3.11.
- remove `toml` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_load_settings_with_tomllib`: Verify that load_settings correctly parses a TOML file using tomllib.

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import tomllib` in candidate: ok

| Risk indicator | Resolved by this change? | Re-checked on the changed copy |
|---|---|---|
| STALE_UPSTREAM | yes | package no longer used |
| OLD_PIN | yes | package no longer used |

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_load_settings_with_tomllib` | passed | passed |

**Verdict: VERIFIED** — no regressions; resolved STALE_UPSTREAM, OLD_PIN

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` The minimum supported Python version is increased from 3.10 to 3.11 to accommodate the use of 'tomllib'.

## Attempts

- #1 gemma-4-31b-it (google, 213.8s): replace → verified

## Open concerns and limitations

- `AI-SUGGESTED` If the project strictly requires support for Python 3.10, this migration will break it. However, the target version is 3.12.14.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
