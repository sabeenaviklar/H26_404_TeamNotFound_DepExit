# Dependency Exit Capsule: requests

Status: **VERIFIED** · risk **medium** (score 23) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 2.31.0; imports requests
- Declared in `requirements.txt:3` as `requests==2.31.0` (runtime)
- Declared in `pyproject.toml:15` as `requests==2.31.0` (runtime)
- PyPI latest 2.34.2 (2026-05-14); upstream psf/requests

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| PRIVATE_API | medium | linkwatch/encoding.py:5 requests.utils._parse_content_type_header | `OBSERVED` |
| MONKEYPATCH | medium | linkwatch/http_patch.py:14 requests.Session.request | `OBSERVED` |
| OLD_PIN | low | 2.31.0 released 2023-05-22, latest 2.34.2 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/checker.py:5` [import] `import requests`
- `linkwatch/checker.py:6` [from-import] `from requests import Session as S`
- `linkwatch/checker.py:13` [reference] `session = S()`
- `linkwatch/checker.py:35` [reference] `except requests.exceptions.ConnectionError:`
- `linkwatch/checker.py:38` [reference] `except requests.exceptions.Timeout:`
- `linkwatch/encoding.py:5` [private-api] `from requests.utils import _parse_content_type_header`
- `linkwatch/encoding.py:5` [from-import] `from requests.utils import _parse_content_type_header`
- `linkwatch/encoding.py:11` [reference] `_, params = _parse_content_type_header(resp.headers.get("Content-Type", ""))`
- `linkwatch/http_patch.py:1` [import] `import requests`
- `linkwatch/http_patch.py:5` [reference] `_original_request = requests.Session.request`
- `linkwatch/http_patch.py:14` [monkeypatch] `requests.Session.request = _request`
- `linkwatch/http_patch.py:14` [reference] `requests.Session.request = _request`

## Baseline execution `MEASURED`

- `import requests`: ok

## Proposed replacement `AI · VERIFIED`

**None** → `-` (model confidence None)




## Migration steps `AI · VERIFIED`


Applied edits `MEASURED`:

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- none

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import requests` in candidate: ok

**Verdict: VERIFIED** — no regressions; every baseline problem attributed to this dependency is resolved

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)

## Attempts

- #1 gemma-4-31b-it (google, 278.4s): None → verified

## Open concerns and limitations

- `OBSERVED` No AI-written tests were produced for this dependency.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
