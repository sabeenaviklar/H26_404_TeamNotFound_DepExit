# Dependency Exit Capsule: pytest

Status: **NOT-REQUIRED** · risk **low** (score 3) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 9.1.1; imports py, pytest
- Declared in `requirements-dev.txt:1` as `pytest` (dev)
- PyPI latest 9.1.1 (2026-06-19); upstream pytest-dev/pytest, archived=False, last push 2026-10-13

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| UNPINNED | low | requirements-dev.txt:1 | `OBSERVED` |

## Usage locations `OBSERVED`

- `tests/conftest.py:6` [import] `import pytest`
- `tests/conftest.py:60` [reference] `@pytest.fixture(scope="session")`
- `tests/conftest.py:70` [reference] `@pytest.fixture`
- `Makefile:11` [text] `python -m pytest`
- `Makefile:11` [text] `python -m pytest`
- `Makefile:20` [text] `docker run --rm $(IMAGE) pytest`
- `Makefile:20` [text] `docker run --rm $(IMAGE) pytest`
- `Dockerfile:12` [text] `CMD ["pytest"]`
- `Dockerfile:12` [text] `CMD ["pytest"]`

## Baseline execution `MEASURED`

- `import py`: ok
- `import pytest`: ok

## Open concerns and limitations

- `OBSERVED` Not selected for migration (below risk threshold or excluded by --only).
