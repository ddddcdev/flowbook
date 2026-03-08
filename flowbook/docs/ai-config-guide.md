# AI Config Creation Guide

**Audience**: AI agents (Cursor, OpenAI API, etc.) that create or edit flowbook configs. Use this guide instead of parsing source code directly.

## Conceptual model

- **config** = whole document (spec + spec_text)
- **config_type** = type/category (input_profile, mapping, plan, etc.)
- **config_name** = config identifier
- **spec** = executable structured configuration
- **spec_text** = full natural-language specification text

## Information sources

| Source | Purpose |
|--------|---------|
| `GET /steps/index` | Step specs: input_schema, output_schema, config_refs (input_key → config_type) |
| `GET /configs/schema/{config_type}` | Config type schema: doc, fields, item_schema, plan_structure |
| `GET /configs/index` | Existing configs (config_type, config_name). Config types list. |
| `flowbook configs schema <config_type>` | CLI: same as schema API |
| `flowbook steps index` | CLI: same as steps index API |

**Correlation**: `config_refs[input_key]` = config_type → use `GET /configs/schema/{config_type}` for full schema.

## Creating configs

### API (primary)

- **Create**: `POST /configs` — body: `{config_type, config_name, spec, spec_text?}`
- **Update (upsert)**: `PUT /configs/{config_type}/{config_name}` — body: `{spec, spec_text?}`

Both require `FLOWBOOK_DATABASE_URL` (Postgres). In-memory store does not persist configs.

### CLI

- **Read schema**: `flowbook configs schema <config_type>` — JSON output
- **Seed from dir**: `flowbook db seed-configs -C configs/` — loads JSON files from directory (no create/update per config)

### Future: OpenAI API flow (3c)

Planned: user prompt → AI returns config spec → 2nd turn provides schema/index info if needed.

## Major config types

### input_profile

Used by: inspect, read_excel_detect_region. Required: `kind_rules` (list of KindRule).

```json
{
  "config_type": "input_profile",
  "config_name": "my_profile",
  "spec": {
    "kind_rules": [
      {"pattern": ".*\\.xlsx$", "kind": "fileA", "plan_name": "import_excel"}
    ],
    "inspect_step_name": "inspect_excel_bytes_v2"
  }
}
```

KindRule: `pattern`, `kind` (file kind), `plan_name`, `match_mode` (optional). Get full schema from `GET /configs/schema/input_profile`.

### mapping

Used by: apply_mapping. Required: `ops` (list of op configs).

```json
{
  "config_type": "mapping",
  "config_name": "my_mapping",
  "spec": {
    "ops": [
      {"op": "rename", "args": {"columns": {"old": "new"}}}
    ]
  }
}
```

### plan

Used by: load_plan. Required: `plan` dict with `name`, `steps`.

```json
{
  "config_type": "plan",
  "config_name": "import_excel",
  "spec": {
    "plan": {
      "name": "import_excel",
      "steps": [
        {"name": "read", "op": "read_excel_bytes", "inputs": {"src_excel_bytes": "@src_excel_bytes"}},
        {"name": "write", "op": "write_excel", "inputs": {"df": "@read/df"}}
      ]
    },
    "result_artifacts": [{"step": "write", "key": "bytes", "label": "Excel file"}]
  }
}
```

Step inputs: `@step_name/output_key` for refs, or literal values. Op names from `GET /steps/index`.

### lookup_table

Used by: lookup_table. Required: `artifact_key` (path to stored DataFrame).

## Workflow for AI

1. **Resolve step → config**: From `GET /steps/index`, read `config_refs` to know which steps need which config types.
2. **Get schema**: `GET /configs/schema/{config_type}` for fields, item_schema (nested), plan_structure (plan only).
3. **Build spec**: Construct spec dict per schema. Validate structure.
4. **Create/update**: `POST /configs` or `PUT /configs/{config_type}/{config_name}`.
