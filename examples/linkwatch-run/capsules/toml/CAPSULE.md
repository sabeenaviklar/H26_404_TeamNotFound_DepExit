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

The 'toml' package is stale (STALE_UPSTREAM, no release in 5 years). Python 3.11+ provides 'tomllib' in the standard library for parsing TOML files, which is the preferred replacement. Since the target Python version is 3.12.14, we can use 'tomllib' and bump the minimum supported Python version to 3.11.

- ✓ 'tomllib' is a standard-library module `OBSERVED` 

## Migration steps `AI · VERIFIED`

1. Update the minimum supported Python version to 3.11 in pyproject.toml to enable the use of tomllib.
2. Replace the 'toml' import with 'tomllib' in linkwatch/config.py.
3. Update the call to toml.load(path) to use tomllib.load(), which requires opening the file in binary mode.
4. Remove the 'toml' dependency from pyproject.toml and requirements.txt.

Applied edits `MEASURED`:
- `pyproject.toml`: applied (exact match) tomllib requires Python 3.11+.
- `linkwatch/config.py`: applied (exact match) Replace stale toml package with standard library tomllib.
- `linkwatch/config.py`: applied (exact match) tomllib.load requires a binary file object, unlike toml.load which accepts a path.
- remove `toml` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_load_settings_migration`: Verify that load_settings correctly parses a TOML file using tomllib.

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import tomllib` in candidate: ok

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_load_settings_migration` | passed | passed |

**Verdict: VERIFIED** — no regressions; every baseline problem attributed to this dependency is resolved

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` The minimum supported Python version is increased from 3.10 to 3.11.

## Attempts

- #1 gemma-4-31b-it (google, 247.1s): replace → verified

## Open concerns and limitations

- `AI-SUGGESTED` If the project ever needs to write TOML files (which is not currently observed in the AST scan), tomllib will not be sufficient as it is read-only.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
