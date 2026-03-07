# Config schema reference

Config kinds and their Spec schemas. Use for AI conf, plan composition, and validation.

## Kinds

| Kind | Description |
|------|-------------|
| `input_profile` | Kind rules, date rule, entity plan map. Used by inspect, read_excel_detect_region. |
| `mapping` | Ops list. Used by apply_mapping. |
| `plan` | Plan config, result_artifacts. Used by load_plan. |
| `lookup_table` | artifact_key. Used by lookup_table. |
| `entity_plan_map` | map, default. Used for routing. |

## Schema API

- **API**: `GET /configs/schema/{kind}` — returns `{kind, doc, fields, nested_types}`.
- **CLI**: `flowbook configs schema <kind>` — JSON output.

Fields may include `item_schema` for list items (KindRule, ResultArtifactSpec). Plan kind includes `plan_structure` for the nested plan dict (name, steps, result_artifacts).

## Field reference

Schema is introspected from `flowbook.core.configs.spec_types`. Each kind has a nested `Spec` TypedDict. See `flowbook/docs/ai-config-guide.md` for AI-oriented creation workflow.
