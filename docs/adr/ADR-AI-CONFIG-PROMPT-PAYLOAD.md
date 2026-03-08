# ADR-AI-CONFIG-PROMPT-PAYLOAD: AI config step prompt payload

## Status

Accepted.

## Context

The `ai_config` step sends a prompt to the OpenAI API to interpret natural-language spec_text and produce a config spec. The prompt payload size affects cost and latency. This ADR documents what we send today and what we may reduce in the future.

## Current payload (items sent to AI API)

| Item | Source | Purpose |
|------|--------|---------|
| Config type | Input | Target config type (mapping, input_profile, plan, etc.) |
| Config name | Input | Target config name |
| Schema | `get_config_type_schema()` | config_type, doc, fields, nested_types, expected_output_schema, plan_structure (plan only) |
| Current spec | `get_config_document()` | Existing spec JSON (reference; new spec_text replaces) |
| Current spec_text | `get_config_document()` | Previous spec_text (user-maintained; diff hint) |
| Context | Input (plan/run inputs) | plan_name, mapping_name, entity_key, etc. |
| Steps index | `engine.registry` | All op specs (op_name, docstring, config_refs, input_schema, output_schema) |
| Configs index | `config_store` | config_types list, configs list (config_type, config_name) |
| Plan spec | `config_store.get_spec(Plan, plan_name)` | Full plan when plan_name in context |
| Spec text | Input | User's new spec_text (natural language) |

### System prompt

- Role: config editor
- Instruction: interpret spec_text, output REPLACES current spec
- expected_output_schema (when present)
- Output: JSON only, no markdown

## Future reduction candidates

| Item | Reduction idea | Rationale |
|------|----------------|-----------|
| Steps index | Send only ops relevant to target config_type | mapping → apply_mapping; input_profile → inspect steps; plan → all. Full index is ~20+ ops. |
| Configs index | Omit or filter by config_type | AI may not need full config list for single-config edit. |
| nested_types | Omit KindRule, DateRule, ResultArtifactSpec when not in target schema | mapping doesn't use KindRule; include only what target needs. |
| Plan spec | Send only when editing plan or when plan references target | If editing mapping, plan structure may be redundant. |
| Schema fields | Trim to target config_type's fields only | Already scoped; nested_types could be trimmed. |

### Not recommended to reduce

- Current spec, current spec_text, spec text: essential for incremental edit
- Config type, config name: minimal
- expected_output_schema: improves output shape
- Context: plan_name etc. useful for plan-aware edits

## Consequences

- Prompt is intentionally verbose during validation phase (3c).
- Cost/latency optimization can be done later by filtering steps index and configs index.
- Any reduction should be configurable (e.g. env flag) to allow A/B comparison.
