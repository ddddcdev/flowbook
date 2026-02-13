# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0a1] - 2026-02-13

### Added

- Minimal public API: `Engine`, `Registry`, `RunSession`, `register_steps`, `UnknownOp`, `ArtifactsStore`, `InMemoryArtifactsStore`, `InMemoryConfigStore`, `NullConfigStore`, `DefaultRunStore`, `__version__`.
- Core package is dependency-light and import-safe (no pandas/openpyxl/psycopg/fastapi at import time).
- Extensions under `flowbook.extensions`: Excel (io, mapping), Postgres (artifacts_store, config_store), steps, FastAPI shell.
- CLI: `flowbook --version`, `flowbook doctor` (stdlib argparse). Doctor reports Python/OS/flowbook version and suggests extras for missing extensions.
- Optional extras: `excel`, `postgres`, `fastapi`, `full` (all three), `dev` (typer, rich, httpx).
- Dev CLI: `flowbook-dev` (Typer) with `--version` and `doctor`; requires `pip install "flowbook[dev]"`.
- Console script: `flowbook = flowbook.cli:main`.

### Changed

- Layout: `flowbook/core/` for engine, registry, runtime, configs, artifacts; `flowbook/extensions/` for Excel, Postgres, FastAPI, steps.
- Version from `importlib.metadata.version("flowbook")` with fallback.

[0.1.0a1]: https://github.com/your-org/flowbook/releases/tag/v0.1.0a1
