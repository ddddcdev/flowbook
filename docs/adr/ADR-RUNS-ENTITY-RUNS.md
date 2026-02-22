# ADR-RUNS-ENTITY-RUNS: runs, entity_runs, and entity status/artifact lookup

## Status

Accepted.

## Context

- **run**: Execution session (run_id). Entry point. config_json holds planner/entry config.
- **entity**: Logical scope (entity_key). Groups artifacts.
- **entity_runs**: Per (run_id, entity_key). status, config_json (executed pipeline).
- **Purpose**: (1) Entity status and artifact lookup. (2) Entity execution result (status + executed config).

## Decision

### Current schema

- **runs**: run_id, status, config_json
- **entity_runs**: (run_id, entity_key) PK, status, artifact_path (primary step output path), config_json, created_at, updated_at
- **artifacts**: (run_id, entity_key, path) — key format `{run_id}/{entity_key}/{path}`

### Scope

- **Planner repeated execution**: Not considered. exec_with_plan_once runs planner once then plan once; entity_runs is upserted twice (last write wins). Sufficient for current use.
- **1 run = 1 entity** in practice. Multiple entities per run are supported but not heavily used.

### Purpose

- **Entity status and artifact lookup**: Query entity_runs by (run_id, entity_key); list artifacts by prefix `{run_id}/{entity_key}/`.
- **Entity execution result**: entity_runs records status + executed config. config_json stays.
- **History and current state**: config.name, status, created_at give "what ran" and "when/how it ended".

### Future: latest_entity_runs

- **May add**: `latest_entity_runs` table or view.
- **Role**: Per (run_id, entity_key), the "latest" row — for convenience when entity_runs gains history (e.g. exec_seq) or for a cleaner query abstraction.
- **Status**: Optional. Not implemented. Add only if needed.

## Consequences

- Status and artifact lookup work via entity_runs and artifacts.
- No latest_entity_runs for now; add later if we introduce exec history or want a dedicated latest view.
