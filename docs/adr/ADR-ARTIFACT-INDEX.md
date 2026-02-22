# ADR-ARTIFACT-INDEX: Artifact index for tenant "latest" queries

## Status

Accepted (updated). Uses **entity_key** instead of namespace_prefix. Artifacts use composite PK (run_id, entity_key, path).

## Context

Artifact keys follow `{run_id}/{entity_key}/{path}`. The **entity_key** is an opaque string (exact-match only) passed via step definition or exec. Index queries use entity_key.

## Decision

### Index layer

- **Protocol**: `ArtifactIndex` with `record(...)`, `list_index(entity_key, limit, order)`, `latest_per_logical(entity_key, limit)`.
- **IndexRow**: run_id, artifact_key, logical_address, entity_key, created_at, content_type.
- **When**: On every output persist (if `RunContext.index` is set), the runner calls `index.record(...)`.
- **entity_key**: Passed explicitly from prepare/exec; not derived from logical address.

### Artifacts table (Postgres)

- **Composite PK**: (run_id, entity_key, path). No artifact_key column.
- **Key format**: `{run_id}/{entity_key}/{path}`. Inputs use entity_key="" for run-level.

### Implementations

- **InMemory**: list + sort; latest_per_logical via distinct-on-logical_address in memory.
- **Postgres**: Reads from `artifacts` (run_id, entity_key, path). Builds artifact_key when returning IndexRow. `record()` is a no-op.

## Consequences

- API or runners query by entity_key for "latest artifacts for entity X".
- Index is optional; runs without an index behave as before (no recording).
