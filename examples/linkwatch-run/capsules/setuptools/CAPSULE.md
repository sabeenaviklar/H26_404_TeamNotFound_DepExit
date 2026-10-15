# Dependency Exit Capsule: setuptools

Status: **VERIFIED** · risk **medium** (score 20) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 75.8.0; imports pkg_resources, setuptools
- Declared in `requirements.txt:9` as `setuptools==75.8.0` (runtime)
- Declared in `pyproject.toml:21` as `setuptools==75.8.0` (runtime)
- PyPI latest 84.0.0 (2026-08-08); upstream pypa/setuptools

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| DEPRECATION_WARNINGS | medium | linkwatch/resources.py:1 DeprecationWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html (run: baseline) | `MEASURED` |
| OUTDATED_PIN | medium | pinned 75.8.0 (2025-01-08), latest 84.0.0 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/resources.py:1` [import] `import pkg_resources`
- `linkwatch/resources.py:7` [reference] `return pkg_resources.resource_filename("linkwatch", "templates")`

## Baseline execution `MEASURED`

- `import pkg_resources`: ok
- `import setuptools`: ok
- Warning (baseline): `linkwatch/resources.py:1` DeprecationWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html
- Warning (pyproject-install): `linkwatch/resources.py:1` DeprecationWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html

## Proposed replacement `AI · VERIFIED`

**remove** → `importlib.resources` (model confidence 1.0)

The package uses `pkg_resources` to locate templates, which is deprecated (DEPRECATION_WARNINGS). The modern standard library replacement is `importlib.resources`. Since `setuptools` is only used for this purpose at runtime, it can be removed from the runtime dependencies.

- ✓ 'importlib.resources' is a standard-library module `OBSERVED` 

## Migration steps `AI · VERIFIED`

1. Replace `pkg_resources.resource_filename` with `importlib.resources.files().joinpath()` in `linkwatch/resources.py`.
2. Remove `setuptools` from the runtime dependencies in `pyproject.toml` and `requirements.txt`.

Applied edits `MEASURED`:
- `linkwatch/resources.py`: applied (exact match) Replace deprecated pkg_resources with stdlib importlib.resources
- `linkwatch/resources.py`: applied (exact match) Use the modern importlib.resources.files API to locate the templates directory
- remove `setuptools` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_template_dir_is_valid`: Ensure template_dir() still returns a valid path to the templates directory

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 1 before → 0 after
- `import importlib` in candidate: ok

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_template_dir_is_valid` | passed | passed |

**Verdict: VERIFIED** — no regressions; every baseline problem attributed to this dependency is resolved

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` importlib.resources.files was introduced in Python 3.9, which is compatible with the project's >=3.10 requirement.

## Attempts

- #1 gemma-4-31b-it (google, 173.5s): remove → verified

## Open concerns and limitations

- `AI-SUGGESTED` If the package is installed in a non-standard way (e.g., as a zip file), importlib.resources.files().joinpath() might return a Traversable object that doesn't resolve to a physical filesystem path via str(). However, for standard pip installations, this is the correct replacement for resource_filename.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
