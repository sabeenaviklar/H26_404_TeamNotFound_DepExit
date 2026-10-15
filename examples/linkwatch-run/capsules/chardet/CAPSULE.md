# Dependency Exit Capsule: chardet

Status: **NOT-REQUIRED** · risk **medium** (score 10) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 5.2.0; imports chardet
- Declared in `requirements.txt:8` as `chardet==5.2.0` (runtime)
- Declared in `pyproject.toml:20` as `chardet==5.2.0` (runtime)
- PyPI latest 7.6.0 (2026-08-14); upstream chardet/chardet

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| OUTDATED_PIN | medium | pinned 5.2.0 (2023-08-01), latest 7.6.0 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/encoding.py:4` [import] `import chardet`
- `linkwatch/encoding.py:15` [reference] `guess = chardet.detect(resp.content)`

## Baseline execution `MEASURED`

- `import chardet`: ok

## Open concerns and limitations

- `OBSERVED` Not selected for migration (below risk threshold or excluded by --only).
