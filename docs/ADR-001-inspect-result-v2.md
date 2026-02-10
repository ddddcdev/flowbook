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

## References

- Implementation: `extensions/steps/inspect_excel_bytes_v2.py` (result construction).
- Consumers: routing by `detected_kind`, tests that assert on inspect output.
