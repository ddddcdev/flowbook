# ADR-REF-DSL: Reference DSL and path grammar

## Status

Accepted. Step input values that are artifact references MUST use the explicit `@` prefix.

## Context

Previously, every string in step inputs was treated as a logical binding name. That made it impossible to pass literal strings (e.g. mapping names, file paths) without overloading semantics. AI and human config authors need a clear, unambiguous rule.

## Decision

### Reference syntax

- A value is a **reference** if and only if it is a `str` and starts with `@`.
- **Short form (implemented)**: `@<logical_address>` means resolve via `ctx.bindings[logical_address]` to an artifact key, then load the artifact.
- **Future form (ADR only)**:
  - `@artifact:<logical_address>` — explicit kind for logical artifact reference.
  - `@key:<artifact_key>` — physical key escape hatch when run_id is known.
- Any string that does **not** start with `@` is a **literal** and is passed through unchanged.

### Logical address

- Opaque key used to index `ctx.bindings`. No fixed number of segments.
- Hierarchical segments separated by `/` are allowed (e.g. `read/df`, `tenantA/batch42/map/df`).
- Canonical shape for step outputs remains `<step.name>/<out_name>` (two segments) but the resolver must not assume exactly two segments.

### Resolution

- Recursive over nested `dict` and `list`; only string values are inspected for `@`.
- Keys of dicts are never resolved; only values are.

## Consequences

- Pipeline configs and plan templates must use `@read/df` (not `read/df`) for refs.
- Literals (mapping name, template name, etc.) stay as plain strings.
