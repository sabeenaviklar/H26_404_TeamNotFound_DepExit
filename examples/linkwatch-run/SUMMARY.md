# DepExit run on `https://github.com/rishrek/LinkWatch`

Commit `f52f3930c8` · Python 3.12.14 · AI: gemma-4-31b-it via google · 2026-10-15T07:01:03+00:00

Baseline tests `MEASURED`: 9 passed / 1 failing

| Dependency | Risk | Score | Status | Proposal |
|---|---|---|---|---|
| [Jinja2](capsules/jinja2/CAPSULE.md) | critical | 90 | verified | upgrade Jinja2>=3.1.0 |
| [nose](capsules/nose/CAPSULE.md) | critical | 66 | verified | remove |
| [MarkupSafe](capsules/markupsafe/CAPSULE.md) | critical | 60 | verified | upgrade Jinja2>=3.1.2 |
| [pydantic](capsules/pydantic/CAPSULE.md) | high | 40 | verified | upgrade pydantic>=2.0 |
| [toml](capsules/toml/CAPSULE.md) | high | 23 | verified | replace tomllib |
| [appdirs](capsules/appdirs/CAPSULE.md) | high | 23 | verified | replace platformdirs |
| [requests](capsules/requests/CAPSULE.md) | medium | 23 | verified | None |
| [setuptools](capsules/setuptools/CAPSULE.md) | medium | 20 | verified | remove importlib.resources |
| [idna](capsules/idna/CAPSULE.md) | medium | 20 | verified | remove |
| [certifi](capsules/certifi/CAPSULE.md) | high | 20 | verified | remove |
| [python-dateutil](capsules/python-dateutil/CAPSULE.md) | medium | 13 | not-required | - |
| [chardet](capsules/chardet/CAPSULE.md) | medium | 10 | not-required | - |
| [six](capsules/six/CAPSULE.md) | low | 6 | not-required | - |
| [pytest](capsules/pytest/CAPSULE.md) | low | 3 | not-required | - |
| [rich](capsules/rich/CAPSULE.md) | low | 3 | not-required | - |
| [click](capsules/click/CAPSULE.md) | none | 0 | not-required | - |

All verified plans applied together `MEASURED`: 19 passed / 0 failing (patch: `combined.patch`)

## Limitations

- Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
- Risk signals from PyPI and GitHub reflect the moment of the run and the public metadata available.
- Security advisories are out of scope for this challenge and are not checked.
