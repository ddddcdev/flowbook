# ADR-ARTIFACT-NAMESPACE: Hierarchical logical addresses and namespace

## Status

Accepted. Logical addresses may be hierarchical; the first segment is used as namespace prefix for indexing.

## Context

Tenant-scoped and batch-scoped runs need a way to group artifacts without putting run_id in the logical address. Queries like "latest artifacts for tenant X" depend on a stable notion of namespace.

## Decision

### Hierarchical logical address

- Logical addresses are opaque keys but **may** use `/`-separated segments (e.g. `tenant_id/batch_id/step/out`).
- The resolver treats the whole string (after stripping `@`) as the key; it does not assume a fixed number of segments.
- Step outputs continue to bind `{step.name}/{out_name}`; callers may use longer paths if they bind them explicitly (e.g. via API or plan).

### Namespace prefix

- For **artifact index** and "latest" queries (stored per-artifact in Postgres, or in a separate index for InMemory), **namespace_prefix** is derived from the logical address:
  - If the address contains `/`, the first segment is the namespace prefix (e.g. `tenantA` from `tenantA/batch42/map/df`).
  - If there is no `/`, the whole address is the prefix.
- This allows indexing and querying by tenant (or top-level segment) without storing run_id in the address.

### run_id

- run_id stays in **physical** artifact_key and metadata only. It must **not** appear inside logical addresses.

## Consequences

- Tenant-aware runners can bind outputs under a prefix (e.g. `tenant123/step/df`) so that list_index and latest_per_logical by `tenant123` return the right rows.
- Cross-run references: current pattern is `bind(name, full_artifact_key)`; preferred future is query index by namespace then bind.
