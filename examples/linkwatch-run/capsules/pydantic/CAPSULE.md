# Dependency Exit Capsule: pydantic

Status: **VERIFIED** · risk **high** (score 40) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 1.10.13; imports pydantic
- Declared in `requirements.txt:5` as `pydantic==1.10.13` (runtime)
- Declared in `pyproject.toml:17` as `pydantic>=2` (runtime)
- PyPI latest 2.14.1 (2026-10-11); upstream sponsors/samuelcolvin

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| DEPRECATION_WARNINGS | medium | site-packages/pydantic/_internal/_config.py:408 UserWarning: Valid config keys have changed in V2: (run: pyproject-install) | `MEASURED` |
| SPEC_CONFLICT | high | requirements.txt:5 ==1.10.13; pyproject.toml:17 >=2; installing via pyproject resolves to 2.14.1 vs 1.10.13 via requirements | `OBSERVED` |
| OUTDATED_PIN | medium | pinned 1.10.13 (2023-09-27), latest 2.14.1 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/config.py:4` [from-import] `from pydantic import BaseModel, validator`
- `linkwatch/config.py:7` [reference] `class Site(BaseModel):`
- `linkwatch/config.py:14` [reference] `@validator("name")`
- `linkwatch/config.py:20` [reference] `@validator("url")`
- `linkwatch/config.py:27` [reference] `class Settings(BaseModel):`

## Baseline execution `MEASURED`

- `import pydantic`: ok
- Warning (pyproject-install): `site-packages/pydantic/_internal/_config.py:408` UserWarning: Valid config keys have changed in V2:

## Proposed replacement `AI · VERIFIED`

**upgrade** → `pydantic>=2` (model confidence 1.0)

The repository has a high-risk SPEC_CONFLICT between requirements.txt (==1.10.13) and pyproject.toml (>=2). It is also using an outdated version of pydantic (1.10.13) and triggering deprecation warnings related to V2 config keys. Upgrading to Pydantic v2 resolves the conflict and aligns the codebase with the declared intent in pyproject.toml.

- ✓ package 'pydantic' exists on PyPI `OBSERVED` latest 2.14.1

## Migration steps `AI · VERIFIED`

1. Update requirements.txt to use pydantic>=2 to resolve the version conflict with pyproject.toml.
2. Update linkwatch/config.py to use Pydantic v2 syntax: replace 'class Config' with 'model_config = ConfigDict(...)', and replace '@validator' with '@field_validator'.

Applied edits `MEASURED`:
- `linkwatch/config.py`: applied (exact match) Import Pydantic v2's field_validator and ConfigDict.
- `linkwatch/config.py`: applied (exact match) Replace v1 Config class with v2 ConfigDict and update anystr_strip_whitespace to str_strip_whitespace.
- `linkwatch/config.py`: applied (exact match) Replace deprecated @validator with @field_validator.
- `linkwatch/config.py`: applied (exact match) Replace deprecated @validator with @field_validator.
- `linkwatch/config.py`: applied (exact match) Replace v1 Config class with v2 ConfigDict.
- set `pydantic>=2` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_site_validation`: Verify that Site validation still works (empty name and invalid URL scheme).
- `test_site_strip_whitespace`: Verify that whitespace stripping is still active in Pydantic v2.
- `test_settings_extra_forbid`: Verify that extra fields are still forbidden in Settings.

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import pydantic` in candidate: ok

| Risk indicator | Resolved by this change? | Re-checked on the changed copy |
|---|---|---|
| DEPRECATION_WARNINGS | yes | 0 attributed warning(s) left |
| SPEC_CONFLICT | yes | manifests agree |
| OUTDATED_PIN | yes | now 2.14.1 |

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_settings_extra_forbid` | passed | passed |
| `test_site_strip_whitespace` | passed | passed |
| `test_site_validation` | passed | passed |

**Verdict: VERIFIED** — no regressions; resolved DEPRECATION_WARNINGS, SPEC_CONFLICT, OUTDATED_PIN

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` Pydantic v2 is a major rewrite; while the logic in this repository is simple, the migration from 'class Config' to 'ConfigDict' and '@validator' to '@field_validator' is required for full compatibility and to remove warnings.

## Attempts

- #1 gemma-4-31b-it (google, 326.2s): upgrade → verified

## Open concerns and limitations

- `AI-SUGGESTED` Pydantic v2 has different internal behavior for some edge cases of validation, though the current usage in this repo is straightforward.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
