# Dependency Exit Capsule: appdirs

Status: **VERIFIED** · risk **high** (score 23) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 1.4.4; imports appdirs
- Declared in `requirements.txt:2` as `appdirs==1.4.4` (runtime)
- Declared in `pyproject.toml:14` as `appdirs==1.4.4` (runtime)
- PyPI latest 1.4.4 (2020-05-11); upstream ActiveState/appdirs

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| STALE_UPSTREAM | high | latest 1.4.4 released 2020-05-11 | `OBSERVED` |
| OLD_PIN | low | 1.4.4 released 2020-05-11, latest 1.4.4 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/cache.py:4` [from-import] `from appdirs import user_cache_dir`
- `linkwatch/cache.py:10` [reference] `path = os.environ.get("LINKWATCH_CACHE_DIR") or user_cache_dir("linkwatch")`

## Baseline execution `MEASURED`

- `import appdirs`: ok

## Proposed replacement `AI · VERIFIED`

**replace** → `platformdirs>=4.0.0` (model confidence 1.0)

The 'appdirs' package is stale (STALE_UPSTREAM), with no releases since 2020. 'platformdirs' is the officially recommended, maintained drop-in replacement that provides the same functionality for locating user directories across different platforms and fully supports Python 3.12.

- ✓ package 'platformdirs' exists on PyPI `OBSERVED` latest 4.13.0

## Migration steps `AI · VERIFIED`

1. Replace 'appdirs' with 'platformdirs' in the project dependency manifests.
2. Update the import statement in 'linkwatch/cache.py' to use 'platformdirs' instead of 'appdirs'.

Applied edits `MEASURED`:
- `linkwatch/cache.py`: applied (exact match) Switch from stale 'appdirs' to maintained 'platformdirs'.
- remove `appdirs` in pyproject.toml, requirements.txt
- add `platformdirs>=4.0.0` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_cache_dir_env_override`: Ensure that the LINKWATCH_CACHE_DIR environment variable still overrides the default cache directory.
- `test_cache_dir_default`: Ensure that cache_dir() returns a valid absolute path when no environment variable is set.

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import platformdirs` in candidate: ok

| Risk indicator | Resolved by this change? | Re-checked on the changed copy |
|---|---|---|
| STALE_UPSTREAM | yes | package no longer used |
| OLD_PIN | yes | package no longer used |

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_cache_dir_default` | passed | passed |
| `test_cache_dir_env_override` | passed | passed |

**Verdict: VERIFIED** — no regressions; resolved STALE_UPSTREAM, OLD_PIN

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` platformdirs.user_cache_dir is a drop-in replacement for appdirs.user_cache_dir and behaves identically on Windows, macOS, and Linux.

## Attempts

- #1 gemma-4-31b-it (google, 151.1s): replace → verified

## Open concerns and limitations

- `AI-SUGGESTED` Minor differences in path resolution on very niche operating systems, though unlikely to affect standard environments.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
