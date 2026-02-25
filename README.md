flowbook — a framework for flexible data flows.

## Quickstart

```sh
pip install flowbook
flowbook --version
flowbook doctor
```

Core-only install has no heavy dependencies. For Excel, Postgres, and FastAPI extensions:

```sh
pip install "flowbook[full]"
```

Optional: add bundled configs for hands-on (no extra deps):

```sh
pip install "flowbook[full,demo]"
```

Dev CLI (Typer/Rich) for local development and demos:

```sh
pip install "flowbook[dev]"
flowbook --version
flowbook doctor
flowbook db reset    # DB reset + seed (needs flowbook[dev])
flowbook db up      # Start Postgres
flowbook api up     # Start API (Docker, template for GCP etc.)
flowbook streamlit up  # Start Streamlit (Docker)
flowbook api       # Run API (uvicorn, poetry)
flowbook hands-on   # API hands-on flow
flowbook streamlit # Streamlit UI (venv)
```

`flowbook doctor` prints Python/OS/flowbook version and suggests `pip install "flowbook[excel]"`, `"flowbook[postgres]"`, `"flowbook[fastapi]"`, or `"flowbook[full]"` for missing extensions.

## Concept

- **Config-driven**: Which steps run, in what order, and how inputs are bound—all come from **config** (plan config, ConfigStore, plan templates). Change the flow without changing framework code.
- **Extend via extensions**: The **behavior** of each step is an **op** registered in a `Registry`. Add new ops in your own package; the framework only resolves `op name → run op`. No need to touch the core.
- **Single data rule**: Data lives only in **Artifacts**; steps receive resolved values and return a dict. Contracts are explicit (e.g. `PortSpec` for inputs).
- **AI-friendly**: Config (templates, rules, mappings) is easy for LLMs to generate or choose. New ops (including AI-backed ones) plug in the same way. You can call LLMs inside an op; the engine stays agnostic.

## Usage (high-level)

1. **Engine** = store (artifacts) + registry (ops) + optional config store. You build it once.
2. **Session** = `with engine.create_run() as session:`. Put inputs (logical name → value), then run a **plan config** (list of steps with `name`, `op`, `inputs`).
3. Optionally run a **planner** first (e.g. `plan_from_template`); it produces a plan config that you then execute in the same session.
4. Steps read from the store (via resolved inputs) and write outputs back; later steps can depend on them. All orchestration is driven by config; new capabilities are new ops in your extensions.

To add your own steps: see [Adding custom steps](docs/adding-custom-steps.md) (minimal: one module + one line at startup; optional: package with entry points). To add CLI commands: see [Adding custom CLI](docs/adding-custom-cli.md).

## Development

- **CI before commit**: `npm run ci` (lint, typecheck, test) runs automatically via [pre-commit](https://pre-commit.com/). It runs only unit (and smoke) tests; integration and e2e are skipped so CI does not require Postgres. After clone, run:
  ```sh
  poetry install
  pre-commit install
  ```
  (The dev group includes full extras so tests can run; for a minimal env use `pip install flowbook` only.)
- **Full test suite** (integration + e2e): Start Postgres (see below), then `npm run test` or `poetry run pytest`. To run only integration: `poetry run pytest -m integration`.
- **Releasing**: See [Releasing](docs/releasing.md). Publish = tag + twine upload. Pre-release (alpha/beta) = push to dev branch only.

## License

Apache License 2.0



## Dev commands (require infra/)

The commands `flowbook db`, `flowbook streamlit`, and `flowbook api` are for **local development**. They expect an `infra/` directory (compose files, env files) in the project. Clone this repo or copy `infra/` to use them.

## Running Postgres with Docker Compose

With flowbook[dev] installed:

```sh
flowbook db up    # Start Postgres (uses infra/.env.postgres)
flowbook db down  # Stop Postgres
```

Use `--env-file PATH` to override; `--no-env-file` to use host env (e.g. poetry's .env).

## Dev / Demo

API and Streamlit UI run from the repo for development and demos.

### API

**Docker (template for GCP Cloud Run etc.):**

```sh
flowbook db up     # Start Postgres first
flowbook api up    # Start API (uses infra/.env.api, network_mode: host → localhost:5432)
flowbook api down  # Stop API
```

**Poetry (development, hot reload):**

```sh
FLOWBOOK_DATABASE_URL=postgresql://flowbook:flowbook@localhost:5432/flowbook poetry run flowbook api
```

Use `--env-file PATH` / `--no-env-file` like db and streamlit.

API docs: <http://localhost:8000/docs>

### Streamlit UI

**Docker (same UX as flowbook db up):**

```sh
flowbook streamlit up    # Start Streamlit (uses infra/.env.streamlit)
flowbook streamlit down  # Stop Streamlit
```

Use `--env-file PATH` to override; `--no-env-file` to use host env (e.g. poetry's .env).

**Local (venv):**

```sh
flowbook streamlit
```

Runs in a separate venv (pandas version compatibility). If you see `ModuleNotFoundError: altair.vegalite.v4`, remove `.venv-ui` and run again.

Requires the API to be running (e.g. `flowbook api` on host). Docker uses `network_mode: host`; `FLOWBOOK_API_URL` from infra/.env.streamlit or host env.

Tabs: Health, Inspect, Import, Artifacts, Export, Download, Configs.

### DB reset (dev only)

**Safety**: Requires `FLOWBOOK_DB_RESET=1`. Refuses non-localhost DSNs.

```sh
FLOWBOOK_DATABASE_URL=... FLOWBOOK_DB_RESET=1 flowbook db reset
```

Truncates artifacts and configs, then seeds from bundled configs (flowbook[demo]) + overlay from `configs/` (default `--config-dir configs`). Use `--config-dir bundled` for bundled only.

### Hands-on flow

```sh
flowbook hands-on
```

Runs Health -> Inspect -> Import -> Artifacts -> Export -> Download (interactive). Requires API up and a fixture. Generate fixture:

```sh
flowbook fixture generate -o tests/fixtures/excel
```