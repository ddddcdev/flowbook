# Steps index reference

Step (op) specs: docstring, config_refs, input_schema, output_schema (name, type, required per field).

## Index API

- **API**: `GET /steps/index` — full index of all step specs.
- **CLI**: `flowbook steps index` — JSON output.

## Step → Config mapping

Steps that reference configs declare `InputSchema` with `Field(json_schema_extra={"x-config-type": "..."})` on config ref fields. Each such field maps to a config type. **Correlate with config schema**: `config_refs[input_key]` = config_type → use `GET /configs/schema/{config_type}` for full schema.

| Input key | Config type | Step(s) |
|-----------|-------------|---------|
| `plan_name` | plan | load_plan |
| `mapping_name` | mapping | apply_mapping |
| `lookup_spec_name` | lookup_table | lookup_table |
| `input_profile_name` | input_profile | inspect, inspect_excel_bytes_v2 |
| `region_profile_name` | input_profile | read_excel_detect_region |

## Individual step

- **API**: `GET /steps/{op_name}` — single step spec including `config_refs`, `input_schema`, `output_schema`.
- **CLI**: `flowbook steps show <op_name>`.
