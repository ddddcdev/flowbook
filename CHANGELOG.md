# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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

[0.1.0a1]: https://github.com/d4cdev/flowbook/releases/tag/v0.1.0a1
