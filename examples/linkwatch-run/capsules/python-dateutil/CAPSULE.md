# Dependency Exit Capsule: python-dateutil

Status: **NOT-REQUIRED** · risk **medium** (score 13) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 2.9.0.post0; imports dateutil
- Declared in `requirements.txt:11` as `python-dateutil` (runtime)
- Declared in `pyproject.toml:23` as `python-dateutil` (runtime)
- PyPI latest 2.9.0.post0 (2024-03-01); upstream dateutil/dateutil

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| UNPINNED | low | requirements.txt:11; pyproject.toml:23 | `OBSERVED` |
| STALE_UPSTREAM | medium | latest 2.9.0.post0 released 2024-03-01 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/dates.py:1` [from-import] `from dateutil import parser`
- `linkwatch/dates.py:8` [reference] `return parser.parse(value)`

## Baseline execution `MEASURED`

- `import dateutil`: ok

## Open concerns and limitations

- `OBSERVED` Not selected for migration (below risk threshold or excluded by --only).
