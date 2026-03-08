"""AI config step: edit config via natural language. Needs flowbook[ai], OPENAI_API_KEY.

Debug: FLOWBOOK_AI_LOG_PROMPT=1 logs full prompt and response at INFO.
FLOWBOOK_LOG_LEVEL=DEBUG logs current_spec and raw response preview.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

from flowbook.core.configs.introspect import get_config_type_schema
from flowbook.core.configs.spec_types import CONFIG_TYPE_TO_SPEC_TYPE
from flowbook.core.logging import get_logger
from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore

logger = get_logger(__name__)


@step("ai_config")
class AiConfigOp(BaseOp):
    """Edit config spec via natural language. Uses OPENAI_API_KEY.
    Initial scope: input_profile kind_rules. Fetches schema and current spec for context."""

    class Inputs(BaseInputs):
        spec_text: str
        """Full spec text. User edits; AI interprets and generates spec. Stored as-is."""
        config_type: str
        config_name: str
        context: dict[str, Any] | None = None
        """Optional plan/run context (e.g. entity_key, target_month). Plan-specific."""

    class Outputs(BaseOutputs):
        config_id: str
        config_type: str
        config_name: str
        edit_summary: str | None = None
        """First 200 chars of spec_text (for trace)."""

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "ai_config requires openai. Install with: pip install flowbook[ai]"
            ) from e

        inp = self.Inputs.model_validate(inputs)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")

        if inp.config_type not in CONFIG_TYPE_TO_SPEC_TYPE:
            raise ValueError(
                f"unknown config_type '{inp.config_type}'. "
                f"Known: {sorted(CONFIG_TYPE_TO_SPEC_TYPE.keys())}"
            )

        # 1) Get current spec and spec_text from store
        config_store = store.configs
        doc = config_store.get_config_document(inp.config_type, inp.config_name)
        current_spec = doc["spec"]
        current_spec_text = doc.get("spec_text") or ""

        _log_prompt_response = os.environ.get("FLOWBOOK_AI_LOG_PROMPT", "").lower() in (
            "1",
            "true",
            "on",
        )
        logger.info(
            "ai_config start",
            extra={
                "config_type": inp.config_type,
                "config_name": inp.config_name,
                "spec_text_len": len(inp.spec_text),
                "context_keys": list(inp.context.keys()) if inp.context else [],
            },
        )
        logger.debug(
            "ai_config current_spec",
            extra={
                "config_type": inp.config_type,
                "config_name": inp.config_name,
                "spec": current_spec,
            },
        )

        # 2) Get schema for context
        schema_info = get_config_type_schema(inp.config_type)

        # 3) Build prompt
        context_parts = [
            f"Config type: {inp.config_type}",
            f"Config name: {inp.config_name}",
            f"Schema: {json.dumps(schema_info, indent=2)}",
            (
                f"Current spec (reference; new spec_text replaces): "
                f"{json.dumps(current_spec, indent=2)}"
            ),
            (
                f"Current spec_text (previous; user edits below):\n{current_spec_text}"
                if current_spec_text
                else "Current spec_text: (none)"
            ),
        ]
        if inp.context:
            context_parts.append(f"Context (plan/run inputs): {json.dumps(inp.context)}")

        # Steps index (op specs) - same as GET /steps/index
        steps_index = _build_steps_index()
        if steps_index:
            context_parts.append(f"Steps index: {json.dumps(steps_index, indent=2)}")

        # Configs index - same as GET /configs/index
        configs_index = _build_configs_index(config_store)
        if configs_index:
            context_parts.append(f"Configs index: {json.dumps(configs_index, indent=2)}")

        # Plan spec when plan_name in context (plan contains steps with ops)
        plan_name = inp.context.get("plan_name") if inp.context else None
        if isinstance(plan_name, str) and plan_name:
            plan_spec = _get_plan_spec(config_store, plan_name)
            if plan_spec:
                context_parts.append(
                    f"Plan '{plan_name}' (context): {json.dumps(plan_spec, indent=2)}"
                )

        expected_schema = schema_info.get("expected_output_schema")
        schema_instruction = ""
        if expected_schema:
            schema_instruction = (
                f" Return JSON matching expected_output_schema: {json.dumps(expected_schema)}."
            )

        system = (
            "You are a config editor. User provides spec_text (full spec in natural language). "
            "Interpret spec_text and produce the complete spec. Output REPLACES current spec."
            f"{schema_instruction} "
            "No markdown, no explanation. Output must parse as JSON."
        )
        user_content = "\n\n".join(context_parts) + f"\n\nSpec text:\n{inp.spec_text}"

        if _log_prompt_response:
            logger.info(
                "ai_config prompt",
                extra={
                    "config_type": inp.config_type,
                    "config_name": inp.config_name,
                    "system": system,
                    "user_content": user_content,
                },
            )

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=2048,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if _log_prompt_response:
            logger.info(
                "ai_config response",
                extra={
                    "config_type": inp.config_type,
                    "config_name": inp.config_name,
                    "raw": raw,
                },
            )
        logger.debug(
            "ai_config ai_raw",
            extra={
                "config_type": inp.config_type,
                "config_name": inp.config_name,
                "raw_preview": raw[:500],
            },
        )

        # 4) Parse AI output (strip markdown code block if present)
        spec = _parse_spec_json(raw)

        # 5) put_spec (spec_text = user input, stored as-is)
        spec_type = CONFIG_TYPE_TO_SPEC_TYPE[inp.config_type]
        config_id = str(uuid.uuid4())
        config_store.put_spec(
            spec_type, inp.config_name, spec, config_id=config_id, spec_text=inp.spec_text
        )

        logger.info(
            "ai_config done",
            extra={
                "config_type": inp.config_type,
                "config_name": inp.config_name,
                "config_id": config_id,
                "spec_keys": list(spec.keys()),
            },
        )

        return self.Outputs(
            config_id=config_id,
            config_type=inp.config_type,
            config_name=inp.config_name,
            edit_summary=(inp.spec_text[:200] + ("..." if len(inp.spec_text) > 200 else "")),
        ).model_dump(mode="python")


def _build_steps_index() -> dict[str, Any] | None:
    """Build steps index (same as GET /steps/index). Uses core Registry + discover_steps."""
    try:
        from flowbook.core.registry.extensions import discover_steps
        from flowbook.core.registry.registry import Registry

        registry = Registry()
        discover_steps(registry)
        specs = []
        for op_name in registry.list_ops():
            spec = registry.get_op_spec(op_name)
            specs.append(
                {
                    "op_name": spec.op_name,
                    "docstring": spec.docstring,
                    "config_refs": spec.config_refs,
                    "input_schema": spec.input_schema,
                    "output_schema": spec.output_schema,
                }
            )
        return {"steps": specs}
    except Exception:
        return None


def _build_configs_index(config_store: Any) -> dict[str, Any] | None:
    """Build configs index (same as GET /configs/index)."""
    try:
        config_types = sorted(CONFIG_TYPE_TO_SPEC_TYPE.keys())
        if hasattr(config_store, "engine") and getattr(config_store, "engine", None):
            from sqlalchemy import text

            engine = config_store.engine
            with engine.begin() as conn:
                rows = conn.execute(
                    text(
                        "SELECT config_type, config_name FROM configs "
                        "WHERE is_active = true ORDER BY config_type, config_name"
                    )
                ).fetchall()
            configs = [{"config_type": r[0], "config_name": r[1]} for r in rows]
        else:
            pairs = list(getattr(config_store, "_specs", {}).keys())
            configs = [{"config_type": k, "config_name": n} for k, n in sorted(pairs)]
        return {"config_types": config_types, "configs": configs}
    except Exception:
        return None


def _get_plan_spec(config_store: Any, plan_name: str) -> dict[str, Any] | None:
    """Get plan spec (full document) when plan_name in context."""
    try:
        from flowbook.core.configs.spec_types import Plan

        spec = config_store.get_spec(Plan, plan_name)
        return dict(spec)
    except Exception:
        return None


def _parse_spec_json(raw: str) -> dict[str, Any]:
    """Extract JSON from AI response. Handles markdown code blocks."""
    s = raw.strip()
    # Strip ```json ... ``` or ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
    if m:
        s = m.group(1).strip()
    return json.loads(s)


register = register_from_steps()
