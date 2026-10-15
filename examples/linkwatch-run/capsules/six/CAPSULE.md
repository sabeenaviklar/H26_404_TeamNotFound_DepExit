# Dependency Exit Capsule: six

Status: **NOT-REQUIRED** · risk **low** (score 6) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 1.17.0; imports six
- Declared in `requirements.txt:7` as `six` (runtime)
- Declared in `pyproject.toml:19` as `six` (runtime)
- PyPI latest 1.17.0 (2024-12-04); upstream benjaminp/six

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| UNUSED | low | no import, reference or CLI invocation found in code, Makefile, Dockerfile or CI files | `OBSERVED` |
| UNPINNED | low | requirements.txt:7; pyproject.toml:19 | `OBSERVED` |

## Usage locations `OBSERVED`

- `-:-` [none] `no usages found`

## Baseline execution `MEASURED`

- `import six`: ok

## Open concerns and limitations

- `OBSERVED` Not selected for migration (below risk threshold or excluded by --only).
