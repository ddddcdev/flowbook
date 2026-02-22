# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- **entity_key + entity_runs**: Replaced namespace with entity_key. `prepare(entity_key=)`, `exec(entity_key=)`. Artifacts scoped by (run_id, entity_key). `entity_runs` table for canonical result per (run_id, entity_key).
- **Artifacts composite PK**: artifacts table uses (run_id, entity_key, path) as primary key; key format `{run_id}/{entity_key}/{path}`. Inputs use `run_id//input/{name}`.

### Removed

- **namespace / namespace_prefix**: Fully removed from ArtifactIndex, artifacts store, and run.

### Changed

- **ArtifactIndex**: `namespace_prefix` → `entity_key` in IndexRow and protocol.
- **RunContext**: Added required `entity_key` field.
- **ADR-ARTIFACT-NAMESPACE**: Superseded. ADR-ARTIFACT-INDEX updated for entity_key.

## [0.1.0a2] - 2026-02-19

### Added

- **Runtime**: Ref DSL (`@ref`, `@ref.path`) and resolver for step inputs; step `_warnings` aggregated into `RunInfo.warnings`.
- **Steps**: Generic DataFrame ops—`merge_df`, `aggregate_df`, `concat_df`, `lookup_table`, `conditional_update`, `check_warn`; `load_artifact_df`, `read_excel_detect_region` (region-based Excel import).
- **Mapping**: `filter_rows` extended with `engine=python`; `expr_df` op.
- **Postgres**: `runs` table; artifact index merged into `artifacts` table.
- **Extensions/API**: Moved to `flowbook.extensions.api`; `/configs` list endpoint; `/export` Form params; `/artifacts/{key}/as_excel`; import params for template, sheet, region.
- **Extensions/UI**: Streamlit demo app (`flowbook streamlit`). Uses separate venv for pandas compatibility.
- **CLI**: Single `flowbook` command; Typer (db, hands-on, fixture, streamlit, artifacts) when `flowbook[dev]` installed. `flowbook.cli` entry point for third-party subcommands. See [Adding custom CLI](docs/adding-custom-cli.md). `flowbook verify` (pypi, wheel) for release checks, available only when run from repo.
- **Configs**: `configs/` layout (input_profiles, mappings, templates, routing) with JSON seeding.

### Changed

- **CLI**: `flowbook-dev` removed. Scripts (reset_db, seed, hands_on, fixture, streamlit) moved into `flowbook.extensions.cli`; invoked via `flowbook db`, `flowbook hands-on`, etc.
- **API**: Layout changed from `apps/api/` to `flowbook/extensions/api/`.

### Removed

- `scripts/` directory (reset_db.py, seed_*.py, hands_on.sh, run_streamlit.sh, verify_*.sh); replaced by `flowbook` subcommands.

### Fixed

- Streamlit/pandas version conflict: removed `ui` extra; `flowbook streamlit` creates `.venv-ui` and runs there.

### Documentation

- ADRs and ref/path grammar spec. Run instructions, reset_db safety (FLOWBOOK_DB_RESET=1).

## [0.1.0a1] - 2026-02-13

### Added

- Minimal public API: `Engine`, `Registry`, `RunSession`, `register_steps`, `discover_steps`, `step`, `register_from_steps`, `UnknownOp`, stores, `__version__`.
- Step discovery via entry points: `flowbook.steps` group; built-in steps and third-party packages register the same way. `discover_steps(registry)` loads all; `register_steps(registry, package=...)` for a single package.
- Optional `@step("name")` decorator and `register_from_steps()` to reduce boilerplate; all built-in steps use them.
- User guide: [Adding custom steps](docs/adding-custom-steps.md) (minimal: runtime register; optional: package with entry point).
- Core package is dependency-light and import-safe (no pandas/openpyxl/psycopg/fastapi at import time).
- Extensions under `flowbook.extensions`: Excel (io, mapping), Postgres (artifacts_store, config_store), steps, FastAPI shell.
- CLI: `flowbook --version`, `flowbook doctor` (stdlib argparse). Doctor reports Python/OS/flowbook version and suggests extras for missing extensions.
- Optional extras: `excel`, `postgres`, `fastapi`, `full` (all three), `dev` (typer, rich, httpx).
- Dev CLI: `flowbook-dev` (Typer) with `--version` and `doctor`; requires `pip install "flowbook[dev]"`.
- Console scripts: `flowbook`, `flowbook-dev`. Entry point: `flowbook.steps` → `flowbook.core.registry.extensions:register_steps`.
- Layout: `flowbook/core/` for engine, registry, runtime, configs, artifacts; `flowbook/extensions/` for Excel, Postgres, FastAPI, steps.
- Version from `importlib.metadata.version("flowbook")` with fallback.

[0.1.0a2]: https://github.com/ddddcdev/flowbook/releases/tag/v0.1.0a2
[0.1.0a1]: https://github.com/ddddcdev/flowbook/releases/tag/v0.1.0a1
