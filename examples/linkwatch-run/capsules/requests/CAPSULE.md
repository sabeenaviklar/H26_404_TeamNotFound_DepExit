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

**upgrade** → `requests==2.34.2` (model confidence 1.0)

Upgrading requests to the latest version (2.34.2) to resolve the OLD_PIN risk. Additionally, replacing the use of the private API `requests.utils._parse_content_type_header` with the standard library `email.message.Message` and removing the global monkeypatch of `requests.Session.request` in favor of explicit session configuration to improve stability and maintainability.

- ✓ package 'requests' exists on PyPI `OBSERVED` latest 2.34.2

## Migration steps `AI · VERIFIED`

1. Upgrade requests version in pyproject.toml and requirements.txt.
2. Replace the private API `requests.utils._parse_content_type_header` with `email.message.Message` in `linkwatch/encoding.py`.
3. Move the User-Agent configuration from the monkeypatch in `linkwatch/http_patch.py` to the `fetch` function in `linkwatch/checker.py`.
4. Disable the monkeypatch assignment in `linkwatch/http_patch.py`.

Applied edits `MEASURED`:
- `linkwatch/encoding.py`: applied (exact match) Replace private requests API with standard library equivalent.
- `linkwatch/encoding.py`: applied (exact match) Use email.message.Message to parse the charset from the Content-Type header.
- `linkwatch/checker.py`: applied (exact match) Explicitly set the User-Agent on the session instead of relying on a global monkeypatch.
- `linkwatch/http_patch.py`: applied (exact match) Remove the global monkeypatch to reduce risk.
- set `requests==2.34.2` in pyproject.toml, requirements.txt

Full patch: [`patch.diff`](patch.diff)

## Suggested tests `AI-SUGGESTED`

- `test_user_agent_preserved`: Ensure the User-Agent is still sent as 'linkwatch/1.0' after removing the monkeypatch.
- `test_encoding_detection_preserved`: Ensure encoding detection still works after replacing the private requests API.

## Executed test results `MEASURED`

- Install: ok; pip check ok
- Repository tests: baseline 9 passed / 1 failing → candidate 9 passed / 1 failing
- Fixed: none; regressions: none
- Warnings attributed to this dependency: 0 before → 0 after
- `import requests` in candidate: ok

| Risk indicator | Resolved by this change? | Re-checked on the changed copy |
|---|---|---|
| PRIVATE_API | yes | no longer used |
| MONKEYPATCH | yes | no longer used |
| OLD_PIN | yes | now 2.34.2 |

| AI-written test | Original dependency | Replacement |
|---|---|---|
| `test_encoding_detection_preserved` | passed | passed |
| `test_user_agent_preserved` | passed | passed |

**Verdict: VERIFIED** — no regressions; resolved PRIVATE_API, MONKEYPATCH, OLD_PIN

## Compatibility gaps

- `MEASURED` Still failing (may be another dependency): tests/test_report.py::test_report_renders_all_sites: ImportError: cannot import name 'soft_unicode' from 'markupsafe' (site-packages/markupsafe/__init__.py)
- `AI-SUGGESTED` The User-Agent is now set per-session in `fetch()` rather than globally for all `requests.Session` instances.

## Attempts

- #1 gemma-4-31b-it (google, 276.3s): upgrade → verified

## Open concerns and limitations

- `AI-SUGGESTED` If other parts of the application (not shown in evidence) rely on the global monkeypatch of `requests.Session.request`, they will no longer send the custom User-Agent.
- `OBSERVED` Verification is only as strong as the repository's own test suite plus the AI-written tests; code paths no test exercises are not proven safe.
- `OBSERVED` Each dependency is verified in isolation, then all verified plans are applied together once; other combinations are not tested.
