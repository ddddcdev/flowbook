# flowbook (package)

Config-driven data flow framework with pluggable ops and extensions.

**Repository**: https://github.com/ddddcdev/flowbook  
**PyPI**: https://pypi.org/project/flowbook/

## Quickstart

```sh
pip install flowbook
flowbook --version
flowbook doctor
```

For Excel, Postgres, FastAPI: `pip install "flowbook[full]"`. For bundled demo configs: `pip install "flowbook[full,demo]"`.

## Concepts

- **Config-driven**: Steps, order, and input binding come from config. Change the flow without changing code.
- **Steps (ops)**: Pluggable steps with inputs/outputs. Plans compose steps. List: `flowbook steps list`. Show spec: `flowbook steps show <op_name>`.
- **Extensions**: Add new ops in your package; framework resolves `op name → run op`.
- **Artifacts**: Data lives in artifacts; steps receive resolved values and return a dict.
- **AI-friendly**: Config is easy for LLMs to generate. New ops (including AI-backed) plug in the same way.

## Usage

1. **Engine** = store + registry + optional config store.
2. **Session** = `with engine.create_run() as session:`. Put inputs, run a plan config (steps with `name`, `op`, `inputs`).
3. Steps read from store and write outputs; later steps can depend on them.

## Dev / Demo

- **API**: `flowbook api` or `npm run api`. Docs: http://localhost:8000/docs
- **Streamlit UI**: `flowbook streamlit`. Requires API. Tabs: Health, Chat, Inspect, Import, Export, Results, Artifacts, Entities, Configs, Steps.
- **Postgres**: `flowbook db up` (Docker) or set `FLOWBOOK_DATABASE_URL`
- **Hands-on**: `flowbook hands-on` for interactive flow
