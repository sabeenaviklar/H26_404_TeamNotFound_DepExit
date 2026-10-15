# Dependency Exit Capsule: click

Status: **NOT-REQUIRED** · risk **none** (score 0) · target `https://github.com/rishrek/LinkWatch` @ `f52f3930c8` · Python 3.12.14

Tags: `OBSERVED` read from files/registries · `MEASURED` produced by execution · `AI-SUGGESTED` Gemma proposal, unverified · `AI · VERIFIED` Gemma proposal confirmed by execution

## Dependency details `OBSERVED`

- Relation: direct; installed 8.5.0; imports click
- Declared in `requirements.txt:6` as `click>=7` (runtime)
- Declared in `pyproject.toml:18` as `click>=7` (runtime)
- PyPI latest 8.5.0 (2026-08-26); upstream pallets/click

## Risk indicators

| Indicator | Severity | Evidence | Source |
|---|---|---|---|

## Usage locations `OBSERVED`

- `linkwatch/cli.py:1` [import] `import click`
- `linkwatch/cli.py:27` [reference] `@click.group()`
- `linkwatch/cli.py:28` [reference] `@click.version_option(__version__, prog_name="linkwatch")`
- `linkwatch/cli.py:34` [reference] `@click.option("--config", "config_path", default="sites.toml", show_default=True,`
- `linkwatch/cli.py:60` [reference] `raise click.ClickException("No cached results, run 'linkwatch check' first.")`
- `linkwatch/cli.py:62` [reference] `click.echo("Wrote %s" % path)`
- `linkwatch/cli.py:51` [reference] `@click.option("--output", "-o", default="status.html", show_default=True,`
- `linkwatch/cli.py:53` [reference] `@click.option("--title", default="linkwatch", show_default=True)`
- `linkwatch/cli.py:68` [reference] `click.echo("Templates: %s" % resources.template_dir())`
- `linkwatch/cli.py:69` [reference] `click.echo("Cache:     %s" % cache.cache_file())`
- `tests/test_report.py:1` [from-import] `from click.testing import CliRunner`
- `tests/test_report.py:20` [reference] `result = CliRunner().invoke(cli, ["report", "-o", str(output)], catch_exceptions=False)`

## Baseline execution `MEASURED`

- `import click`: ok

## Open concerns and limitations

- `OBSERVED` Not selected for migration (below risk threshold or excluded by --only).
