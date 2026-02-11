# ADR-001: inspect_result_v2 schema

## Status

Accepted. Output of `inspect_excel_bytes_v2` step (and any step that returns an inspect result) MUST conform to this schema when using `schema_version: "inspect_result_v2"`.

## Context

The inspect step returns a structured result (filename matching, kind, effective date, evidence). The shape was implicit in code. Externalizing it enables stable clients, tests, and future steps that consume inspect results.

## Decision

### Top-level output

The step returns a dict with one public key:

- `result` (dict): the inspect result conforming to the schema below.

### inspect_result_v2 schema (the value of `result`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Literal `"inspect_result_v2"`. |
| `input_profile_name` | string | yes | Name of the input_profile config used. |
| `filename` | string | yes | Filename (or path) that was inspected. |
| `detected_kind` | string \| null | yes | Kind matched by kind_rules (e.g. `"fileA"`), or null if no rule matched. |
| `effective_date` | string \| null | yes | Normalized date string (e.g. `"YYYY-MM-DD"`) from date_rule, or null. |
| `evidence` | object | yes | Evidence for matching and date. |

### evidence object

| Field | Type | Description |
|-------|------|-------------|
| `matcher` | string | e.g. `"filename_regex"`. |
| `matched_pattern` | string \| null | The regex pattern that matched, or null. |
| `date` | object | `sheet`, `cell`, `raw_value` from date_rule evaluation. |

### Versioning policy

- **Additive only**: New optional fields may be added. Existing fields MUST NOT be removed or renamed for the same `schema_version`.
- **Breaking change**: Bump `schema_version` (e.g. to `inspect_result_v3`) and document in a new ADR. Consumers that rely on the old shape should support both until migration.

### Consumer contract

Consumers of the inspect result MUST use only the following keys for the stated purposes. This keeps logging, routing, and tests aligned.

| Consumer | Keys used | Purpose |
|----------|-----------|--------|
| **Routing** | `detected_kind` | Look up template name from routing config (`map[detected_kind]` or `default`). Null means use `default`. |
| **Plan selection** | (derived from routing) | Plan is chosen by the template name resolved from `detected_kind` via routing. No direct key beyond `detected_kind`. |
| **Tests / assertions** | `schema_version`, `input_profile_name`, `detected_kind`, `effective_date`, `evidence` | Assert output shape and values. |
| **Logging (recommended)** | `detected_kind`, `input_profile_name` | On failure, log which profile and kind were used so operators can trace. |

For `inspect_result_v1` (filename-based inspect): same consumer contract; the result dict is the artifact value (no `result` wrapper). Routing and plan selection use `detected_kind` the same way.

## References

- Implementation: `extensions/steps/inspect_excel_bytes_v2.py` (result construction), `extensions/steps/inspect.py` (v1).
- Routing: resolves template name from `result["detected_kind"]` and routing config (e.g. `test_excel_real_e2e._resolve_template_name`).
