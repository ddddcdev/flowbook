# ADR-ARTIFACT-INDEX: Artifact index for tenant "latest" queries

## Status

Accepted. An optional artifact index layer records each persisted output for querying by namespace.

## Context

Physical keys are `{run_id}/{path}`. Listing by prefix cannot efficiently answer "latest artifacts for tenant X" when tenant is encoded in the logical address. A separate index is needed.

## Decision

### Index layer

- **Protocol**: `ArtifactIndex` with `record(...)`, `list_index(namespace_prefix, limit, order)`, `latest_per_logical(namespace_prefix, limit)`.
- **IndexRow**: run_id, artifact_key, logical_address, namespace_prefix, created_at, content_type.
- **When**: On every output persist (if `RunContext.index` is set), the runner calls `index.record(...)`.
- **namespace_prefix**: Derived from logical_address (first segment, or whole address if no `/`).

### run_id

- run_id is **not** part of the logical address. It is stored only in the index row and in the physical artifact_key.

### Usage

- "Latest" retrieval does not require `@key:...` in config. The caller queries the index (e.g. `latest_per_logical(tenant_id)`), then binds the returned artifact keys for the run (existing `bind(name, artifact_key)` pattern).

### Implementations

- **InMemory**: For tests and single-process; list + sort; latest_per_logical via distinct-on-logical_address in memory.
- **Postgres**: Table `artifact_index`; list_index by prefix + order; latest_per_logical via window (ROW_NUMBER PARTITION BY logical_address ORDER BY created_at DESC).

## Consequences

- API or runners can offer "latest artifacts for tenant" by calling the index then preparing bindings for execution.
- Index is optional; runs without an index behave as before (no recording).
