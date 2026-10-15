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

**upgrade** → `pydantic>=2.0` (model confidence 1.0)

The repository has a SPEC_CONFLICT between requirements.txt (==1.10.13) and pyproject.toml (>=2). The installed version is 1.10.13, but the code is triggering V2 deprecation warnings during installation/execution. Upgrading to Pydantic V2 aligns the manifests and removes the risk of using an outdated major version.

- ✓ package 'pydantic' exists on PyPI `OBSERVED` latest 2.14.1

## Migration steps `AI · VERIFIED`

1. Update pydantic version in requirements.txt to match pyproject.toml (>=2.0).
2. Update linkwatch/config.py to use Pydantic V2 syntax: replace 'validator' with 'field_validator', 'class Config' with 'model_config = ConfigDict(...)', and add '@classmethod' to validators.

Applied edits `MEASURED`:
- `linkwatch/config.py`: applied (exact match) Import V2 replacements for validator and Config
- `linkwatch/config.py`: applied (exact match) Migrate V1 Config to V2 ConfigDict
- `linkwatch/config.py`: applied (exact match) Migrate V1 validator to V2 field_validator
- `linkwatch/config.py`: applied (exact match) Migrate V1 validator to V2 field_validator
- `linkwatch/config.py`: applied (exact match) Migrate V1 Config to V2 ConfigDict
- set `pydantic>=2.0` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_pydantic_v2_migration`: Verify that Site and Settings validation still works as expected with Pydantic V2

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import pydantic` in candidate: ok

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_settings_validation` | passed | passed |
| `test_site_validation` | passed | passed |

**Verdict: VERIFIED** — no regressions; every baseline problem attributed to this dependency is resolved

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` Pydantic V2 introduces breaking changes in configuration and validation decorators. The migration uses ConfigDict and field_validator.

## Attempts

- #1 gemma-4-31b-it (google, 245.4s): upgrade → verified

## Open concerns and limitations

- `AI-SUGGESTED` If other parts of the code (not found in AST scan) use Pydantic V1 features, they might break.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
