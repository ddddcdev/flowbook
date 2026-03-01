flowbook — a framework for flexible data flows.

## Quickstart

```sh
pip install flowbook
flowbook --version
flowbook doctor
```

Core-only install has no heavy dependencies. For Excel (.xlsx, .xls), Postgres, and FastAPI extensions:

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
flowbook db init    # Create schema (first-time only)
flowbook db reset   # DB reset + seed (needs flowbook[dev])
flowbook db up      # Start Postgres (Docker, optional)
flowbook api       # Run API (uvicorn)
flowbook streamlit # Streamlit UI (venv)
flowbook hands-on   # API hands-on flow
flowbook steps list # List available steps (ops)
flowbook steps show <op_name>  # Show step spec (inputs, outputs)
```

`flowbook doctor` prints Python/OS/flowbook version and suggests `pip install "flowbook[excel]"`, `"flowbook[postgres]"`, `"flowbook[fastapi]"`, or `"flowbook[full]"` for missing extensions.

## Concept

- **Config-driven**: Which steps run, in what order, and how inputs are bound—all come from **config** (plan config, ConfigStore, plan templates). Change the flow without changing framework code.
- **Steps (ops)**: Flowbook uses pluggable **steps** (ops). Each step has inputs and outputs; plans compose steps. List available steps: `flowbook steps list`. Show step details (docstring, inputs, outputs): `flowbook steps show <op_name>`. API: `GET /steps`, `GET /steps/{op_name}`. Streamlit: Steps tab.
- **Extend via extensions**: The **behavior** of each step is an **op** registered in a `Registry`. Add new ops in your own package; the framework only resolves `op name → run op`. No need to touch the core.
- **Single data rule**: Data lives only in **Artifacts**; steps receive resolved values and return a dict. Contracts are explicit (e.g. `PortSpec` for inputs).
- **AI-friendly**: Config (templates, rules, mappings) is easy for LLMs to generate or choose. New ops (including AI-backed ones) plug in the same way. You can call LLMs inside an op; the engine stays agnostic.

## Usage (high-level)

1. **Engine** = store (artifacts) + registry (ops) + optional config store. You build it once.
2. **Session** = `with engine.create_run() as session:`. Put inputs (logical name → value), then run a **plan config** (list of steps with `name`, `op`, `inputs`).
3. Optionally run a **planner** first (e.g. `plan_from_template`); it produces a plan config that you then execute in the same session.
4. Steps read from the store (via resolved inputs) and write outputs back; later steps can depend on them. All orchestration is driven by config; new capabilities are new ops in your extensions.

To add your own steps: see [Adding custom steps](docs/adding-custom-steps.md) (minimal: one module + one line at startup; optional: package with entry points). To compose plans from steps: see [Plan from steps](docs/steps/plan-from-steps.md). To add CLI commands: see [Adding custom CLI](docs/adding-custom-cli.md).

## Development

- **CI before commit**: `npm run ci` (lint, typecheck, test) runs automatically via [pre-commit](https://pre-commit.com/). It runs only unit (and smoke) tests; integration and e2e are skipped so CI does not require Postgres. After clone, run:
  ```sh
  uv sync
  pre-commit install
  ```
  (The dev group includes full extras so tests can run; for a minimal env use `pip install flowbook` only.)
- **Full test suite** (integration + e2e): Start Postgres (see below), then `npm run test` or `uv run pytest`. To run only integration: `uv run pytest -m integration`.
- **Releasing**: See [Releasing](docs/releasing.md). Publish = tag + twine upload. Pre-release (alpha/beta) = push to dev branch only.

## License

Apache License 2.0



## Dev commands

The commands below are for **local development**. The Docker subcommands (`flowbook db up`, `flowbook api up`, `flowbook streamlit up`) require an `infra/` directory (compose files, env files). Clone this repo or copy `infra/` to use them.

**`.env`**: uv does not auto-load `.env`. Use `uv run --env-file .env flowbook ...` or `export UV_ENV_FILE=.env`. Or use `npm run api` / `npm run hands-on` which pass `--env-file .env`.

## Dev / Demo

API and Streamlit UI run from the repo for development and demos. Postgres is required for the API.

### Postgres

Run Postgres (local install, cloud, or Docker):

```sh
# Option: Docker Compose (requires infra/)
flowbook db up    # Start Postgres (uses infra/.env.postgres)
flowbook db down  # Stop Postgres
```

Use `--env-file PATH` / `--no-env-file` to override. Or run Postgres yourself and set `FLOWBOOK_DATABASE_URL`.

**First-time**: Docker Compose runs init scripts automatically. For cloud or local Postgres, run `FLOWBOOK_DB_RESET=1 flowbook db init` to create the schema.

### API

```sh
# With .env: cp .env.example .env, then:
npm run api
# Or: uv run --env-file .env flowbook api
# Or: UV_ENV_FILE=.env uv run flowbook api
```

API docs: <http://localhost:8000/docs>

Docker: `flowbook api up` / `flowbook api down` (uses infra/.env.api, network_mode: host). Cloud deploy: `docker build -f infra/Dockerfile.api -t flowbook-api .` — set `FLOWBOOK_DATABASE_URL` via env/secrets; image listens on `$PORT`.

### Streamlit UI

```sh
flowbook streamlit
```

Runs in a separate venv (pandas version compatibility). Requires the API. If you see `ModuleNotFoundError: altair.vegalite.v4`, remove `.venv-ui` and run again.

Tabs: Steps, Inspect, Import, Artifacts, Export, Download, Configs.

Docker: `flowbook streamlit up` / `flowbook streamlit down` (uses infra/.env.streamlit). Cloud deploy: `docker build -f infra/Dockerfile.streamlit -t flowbook-streamlit .` — set `FLOWBOOK_API_URL` via env/secrets.

### DB init and reset (dev only)

**First-time setup** (empty DB, no tables): Create schema before reset. Requires `FLOWBOOK_DB_RESET=1` and localhost DSN.

**Reset** (truncate + seed): Same safety requirements. Run `flowbook db init` first if the DB has no schema.

```sh
FLOWBOOK_DATABASE_URL=... FLOWBOOK_DB_RESET=1 flowbook db init
FLOWBOOK_DATABASE_URL=... FLOWBOOK_DB_RESET=1 flowbook db reset
```

`flowbook db init` creates entities, runs, results, artifacts, configs. `flowbook db reset` truncates them and seeds from bundled configs (flowbook[demo]) + overlay from `configs/` (default `--config-dir configs`). Use `--config-dir bundled` for bundled only.

### Hands-on flow

```sh
flowbook hands-on
```

Runs Health -> Inspect -> Import -> Artifacts -> Export -> Download (interactive). Requires API up and a fixture. Excel import supports .xlsx and .xls (region-based import uses df-based detection). Generate fixture:

```sh
flowbook fixture generate -o tests/fixtures/excel
```