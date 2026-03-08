# Plan from Steps

This guide describes how to compose a **plan** from **steps** (ops). It is intended for AI and humans building plan configs.

## Plan config schema

A plan config is a JSON-like dict:

```json
{
  "name": "optional_plan_name",
  "steps": [
    {"name": "step_instance_name", "op": "op_registry_key", "inputs": {...}}
  ],
  "result_artifacts": [{"step": "step_name", "key": "output_key", "label": "optional"}]
}
```

- **steps**: Required. List of step configs. Order is execution order (sequential).
- **name**: Optional. Human-readable plan name for logging.
- **result_artifacts**: Optional. Declares which step outputs are "main results" for UI/export. If absent, the last step's first output is used.

## Step config

Each step in `steps` has:

| Field | Required | Description |
|-------|----------|-------------|
| **name** | Yes | Instance name for this step. Used in refs: `@step_name/output_key`. Must be unique within the plan. |
| **op** | Yes | Registry key (e.g. `add`, `read_excel_detect_region`). Must be registered via `discover_steps` or custom `register`. |
| **inputs** | Yes | Dict of input key → value. Values can be refs (`@...`) or literals. |

## Discovering steps

- **CLI**: `flowbook steps list` — list all op names. `flowbook steps show <op_name>` — docstring, inputs (required/optional), outputs.
- **API**: `GET /steps` — `{"ops": ["add", "read_excel_detect_region", ...]}`. `GET /steps/{op_name}` — full spec.
- **Streamlit**: Steps tab — list and select for details.

## Reference grammar

Input values starting with `@` are **refs**; the rest is the logical address.

- `@binding_key` — from session bindings (e.g. `put_input("x", 1)` → `@x`).
- `@step_name/output_key` — from a previous step's output (e.g. `@read/df`).

See [ref-and-path-grammar.md](../spec/ref-and-path-grammar.md) for details.

## Plans

The `load_plan` op loads a pre-defined plan from ConfigStore (Plan config type). Use when the plan structure is fixed and only bindings vary.

```json
{
  "steps": [
    {
      "name": "planner",
      "op": "load_plan",
      "inputs": {"plan_name": "import_excel_region"}
    }
  ]
}
```

The planner step outputs `plan` (and optionally `result_artifacts`). Use `exec_with_planner_once` to run planner → execute resulting plan in one call.

## Example flows

**Simple add**:
```json
{
  "steps": [
    {"name": "add", "op": "add", "inputs": {"x": "@x", "y": "@y"}}
  ]
}
```
Bindings: `put_input("x", 1)`, `put_input("y", 2)`.

**Import Excel (region detect)**:
```json
{
  "steps": [
    {
      "name": "read",
      "op": "read_excel_detect_region",
      "inputs": {
        "src_excel_bytes": "@src_excel_bytes",
        "src_excel_filename": "@src_excel_filename",
        "region_profile_name": "detail_region",
        "sheet": 0
      }
    }
  ],
  "result_artifacts": [{"step": "read", "key": "df", "label": "Imported table"}]
}
```

**Planner + plan** (two-phase):
1. Run planner: `load_plan` with `plan_name`.
2. Planner outputs `plan` (plan config).
3. Execute that plan in the same session (same run_id, bindings available).
