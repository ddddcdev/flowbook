flowbook — a framework for flexible data flows.

## Concept

- **Config-driven**: Which steps run, in what order, and how inputs are bound—all come from **config** (pipeline config, ConfigStore, plan templates). Change the flow without changing framework code.
- **Extend via extensions**: The **behavior** of each step is an **op** registered in a `Registry`. Add new ops in your own package; the framework only resolves `op name → run op`. No need to touch the core.
- **Single data rule**: Data lives only in **Artifacts**; steps receive resolved values and return a dict. Contracts are explicit (e.g. `PortSpec` for inputs).
- **AI-friendly**: Config (templates, rules, mappings) is easy for LLMs to generate or choose. New ops (including AI-backed ones) plug in the same way. You can call LLMs inside an op; the engine stays agnostic.

## Usage (high-level)

1. **Engine** = store (artifacts) + registry (ops) + optional config store. You build it once.
2. **Session** = `engine.prepare()`. Put inputs (logical name → value), then run a **pipeline config** (list of steps with `name`, `op`, `inputs`).
3. Optionally run a **planner** first (e.g. `plan_from_template`); it produces a plan config that you then execute in the same session.
4. Steps read from the store (via resolved inputs) and write outputs back; later steps can depend on them. All orchestration is driven by config; new capabilities are new ops in your extensions.

(Concrete quickstart and extension how-to will follow.)

## Development

- **CI before commit**: `npm run ci` (lint, typecheck, test) runs automatically via [pre-commit](https://pre-commit.com/). After clone, run:
  ```sh
  poetry install
  pre-commit install
  ```

## License

Apache License 2.0



## Running Postgres with Docker Compose

```sh
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres down -v
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres up -d
docker compose -f infra/compose.postgres.yml --env-file infra/.env.postgres logs -f
```