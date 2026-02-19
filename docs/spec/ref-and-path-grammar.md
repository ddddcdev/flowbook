# Spec: Address & Ref Grammar

This document gives copy-pastable examples of valid and invalid refs and logical addresses for Flowbook step inputs.

## Reference strings

A **reference** is a string value that starts with `@`. The rest of the string is the **logical address** (used to look up `ctx.bindings`).

### Valid refs

```json
"@read/df"
"@load_a/df"
"@tenantA/batch42/map/df"
"@step/out"
"@a"
```

### Invalid (treated as literals)

- `"read/df"` — missing `@`; will not be resolved, passed as literal string.
- `"@ "` — payload is empty/whitespace; may fail at resolution if not bound.
- No spaces: `"@ read/df"` has payload ` read/df` (leading space); valid syntax but unusual.

### Future syntax (not implemented)

- `@artifact:<logical_address>` — explicit kind (ADR only).
- `@key:<artifact_key>` — physical key escape hatch (ADR only).

## Logical address

- Opaque key. Segments may be separated by `/`.
- No fixed length. Examples: `read/df` (2 segments), `tenant/id/step/out` (4 segments).
- **Must not** contain run_id. run_id is only in physical artifact_key.

### Valid logical addresses

```
read/df
load_a/df
tenantA/batch42/map/df
step/out
x
```

### Invalid

- Empty after `@`: `@` — no logical address.
- run_id in address: `@run-123/step/df` — run_id does not belong in logical address (use physical key via future `@key:...` if needed).

## Step inputs (mixed refs and literals)

Valid example:

```json
{
  "left": "@load_a/df",
  "right": "@load_b/df",
  "on": "id",
  "how": "left"
}
```

- `left`, `right`: refs (resolved to DataFrames).
- `on`, `how`: literals (strings passed as-is).

List of refs:

```json
{
  "dfs": ["@a/df", "@b/df"]
}
```

- Resolver resolves each list element; `dfs` becomes a list of two DataFrames.
