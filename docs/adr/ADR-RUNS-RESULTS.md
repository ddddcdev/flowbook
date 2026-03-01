# ADR-RUNS-RESULTS: runs, results, and entity status/artifact lookup

## Status

Accepted.

## Context

- **run**: Execution session (run_id). Entry point. config_json holds planner/entry config.
- **entity**: Logical scope (entity_key). Groups artifacts.
- **results**: Per (run_id, entity_key). status, config_json (executed plan).
- **Purpose**: (1) Entity status and artifact lookup. (2) Entity execution result (status + executed config).

## Decision

### Current schema

- **runs**: run_id, status, config_json
- **results**: (run_id, entity_key) PK, status, result_artifacts_json, config_json, created_at, updated_at
- **artifacts**: (run_id, entity_key, path) — key format `{run_id}/{entity_key}/{path}`

### Scope

- **Planner repeated execution**: Not considered. exec_with_planner_once runs planner once then plan once; results is upserted twice (last write wins). Sufficient for current use.
- **1 run = 1 entity** in practice. Multiple entities per run are supported but not heavily used.

### Purpose

- **Entity status and artifact lookup**: Query results by (run_id, entity_key); list artifacts by prefix `{run_id}/{entity_key}/`.
- **Entity execution result**: results records status + executed config. config_json stays.
- **History and current state**: config.name, status, created_at give "what ran" and "when/how it ended".

### Store support

- **PostgresArtifactsStore**: Full support for runs, results, artifacts. Use for production and multi-run workflows.
- **InMemoryArtifactsStore**: Single-run execution only. Does not support runs or results. Use for development and smoke tests only.

### latest_results

- **Status**: API-only (query over results). No new table.
- **Role**: Per entity_key, the "latest" row (updated_at max) — for convenience when querying latest run per entity.

## Consequences

- Status and artifact lookup work via results and artifacts.
- latest_results: API returns rows with max(updated_at) per entity_key; no new table.
