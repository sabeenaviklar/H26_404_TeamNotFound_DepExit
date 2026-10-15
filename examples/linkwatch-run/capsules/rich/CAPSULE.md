# Dependency Exit Capsule: rich

Status: **NOT-REQUIRED** · risk **low** (score 3) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 15.0.0; imports rich
- Declared in `requirements.txt:12` as `rich` (runtime)
- Declared in `pyproject.toml:24` as `rich` (runtime)
- PyPI latest 15.0.0 (2026-04-12); upstream Textualize/rich

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|
| UNPINNED | low | requirements.txt:12; pyproject.toml:24 | `OBSERVED` |

## Usage locations `OBSERVED`

- `linkwatch/cli.py:2` [from-import] `from rich.console import Console`
- `linkwatch/cli.py:3` [from-import] `from rich.live import Live`
- `linkwatch/cli.py:4` [from-import] `from rich.table import Table`
- `linkwatch/cli.py:9` [reference] `console = Console()`
- `linkwatch/cli.py:13` [reference] `table = Table(title=title)`
- `linkwatch/cli.py:40` [reference] `with Live(build_table(settings.title, results), console=console,`

## Baseline execution `MEASURED`

- `import rich`: ok

## Open concerns and limitations

- `OBSERVED` Not selected for migration (below risk threshold or excluded by --only).
