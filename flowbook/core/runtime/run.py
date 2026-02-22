"""
run:
- Executes a Plan sequentially.
- Step.inputs may contain refs (@<logical_address>), literals, or nested dict/list.
  Refs are resolved via RunContext.bindings (logical -> artifact_key -> store.get_any).
  Only strings starting with @ are refs; others are passed through.
- Ops MUST NOT assume artifact keys; they receive resolved values.
- Preflight: refs exist in bindings, unregistered op, op.Inputs (required/surplus).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

from flowbook.core.artifacts.key_utils import build_artifact_key
from flowbook.core.artifacts.store import JsonValue
from flowbook.core.registry.registry import UnknownOp
from flowbook.core.runtime.context import RunContext
from flowbook.core.runtime.resolve import collect_refs_in_inputs, resolve_value
from flowbook.core.runtime.store import RunStore
from flowbook.core.runtime.types import Plan, RunInfo, Step, StepRunInfo


def _validate_step_contracts(plan: Plan, ctx: RunContext) -> None:
    """
    Preflight: every step has a registered op; if op has Inputs with non-empty allowed_keys,
    step inputs satisfy required and have no surplus keys.
    Raises RuntimeError with run_id, step name, and missing/surplus keys.
    """
    for step in plan.steps:
        try:
            op = ctx.registry.get(step.op)
        except UnknownOp as e:
            raise RuntimeError(
                f"unregistered op in run_id='{ctx.run_id}': step '{step.name}' op '{e.args[0]}'"
            ) from e

        spec = op.Inputs
        if not spec.allowed_keys():
            continue
        param_keys = set(step.inputs.keys())
        required_set = set(spec.REQUIRED)
        allowed = spec.allowed_keys()
        missing = required_set - param_keys
        surplus = param_keys - allowed
        if missing:
            raise RuntimeError(
                f"missing required inputs in run_id='{ctx.run_id}': "
                f"step '{step.name}' keys {sorted(missing)}"
            )
        if surplus:
            raise RuntimeError(
                f"surplus inputs in run_id='{ctx.run_id}': "
                f"step '{step.name}' keys {sorted(surplus)}"
            )


def _validate_step_inputs(step: Step, ctx: RunContext) -> None:
    """
    Ensure all refs (strings starting with @) in step inputs exist in bindings.
    Only ref logical addresses are validated; literals are not looked up.
    """
    refs = collect_refs_in_inputs(step.inputs)
    missing = [logical for logical in refs if logical not in ctx.bindings]
    if missing:
        raise RuntimeError(
            f"missing required input keys in run_id='{ctx.run_id}': "
            f"step '{step.name}' keys {sorted(missing)}"
        )


def _resolve_inputs(step: Step, ctx: RunContext) -> dict[str, object]:
    """Resolve step inputs recursively: @ref -> bindings -> store.get_any; literals unchanged."""
    resolved: dict[str, object] = {}
    for param, raw_value in step.inputs.items():
        resolved[param] = resolve_value(raw_value, ctx)
    return resolved


def _content_type_for_value(value: JsonValue | bytes | object) -> str:
    if isinstance(value, bytes):
        return "application/octet-stream"
    import pandas as pd

    if isinstance(value, pd.DataFrame):
        return "application/vnd.dataframe"
    return "application/json"


def _persist_output(
    store: RunStore,
    out_key: str,
    value: JsonValue | bytes | object,
    *,
    created_at: object = None,
) -> None:
    meta = {}
    if created_at is not None:
        meta["created_at"] = created_at
    if isinstance(value, bytes):
        store.put_bytes(out_key, value, **meta)
        return
    # Lazy import to keep core import-safe (no pandas at import time).
    import pandas as pd

    if isinstance(value, pd.DataFrame):
        store.put_df(out_key, value, **meta)
        return
    store.put(out_key, cast(JsonValue, value), **meta)


def _upsert_entity_run(
    store: RunStore,
    run_id: str,
    entity_key: str,
    status: str,
    artifact_path: str | None = None,
    run_config_json: str | None = None,
    entity_config_json: str | None = None,
) -> None:
    """Upsert entity_runs if store supports it. artifact_path=primary step output path."""
    upsert = getattr(store, "upsert_entity_run", None)
    if callable(upsert):
        upsert(
            run_id,
            entity_key,
            status,
            artifact_path=artifact_path,
            run_config_json=run_config_json,
            entity_config_json=entity_config_json,
        )


def run(plan: Plan, ctx: RunContext) -> RunInfo:
    info = RunInfo(run_id=ctx.run_id, status="running")
    _upsert_entity_run(
        ctx.store,
        ctx.run_id,
        ctx.entity_key,
        "running",
        run_config_json=ctx.run_config_json,
        entity_config_json=ctx.entity_config_json,
    )

    try:
        _validate_step_contracts(plan, ctx)

        for step in plan.steps:
            _validate_step_inputs(step, ctx)
            step_info = StepRunInfo(
                name=step.name,
                status="running",
                inputs=dict(step.inputs),
            )
            info.steps.append(step_info)

            # Resolve inputs: artifact key -> value
            resolved_inputs = _resolve_inputs(step, ctx)

            step_op = ctx.registry.get(step.op)

            step_output = step_op(resolved_inputs, ctx.store)
            if not isinstance(step_output, dict):
                got = type(step_output).__name__
                raise TypeError(f"Step '{step.name}' must return dict[str, Any]; got {got}")

            # Aggregate op _warnings into run-level warnings (do not persist as artifact)
            _warnings = step_output.get("_warnings")
            if isinstance(_warnings, list):
                for msg in _warnings:
                    if isinstance(msg, str):
                        info.warnings.append(msg)

            out_spec = step_op.Outputs
            if out_spec.allowed_keys():
                public_keys = {k for k in step_output.keys() if not k.startswith("_")}
                surplus = public_keys - out_spec.allowed_keys()
                if surplus:
                    raise RuntimeError(
                        f"step '{step.name}' returned keys not in Outputs.KEYS: {sorted(surplus)}"
                    )

            # Persist outputs to artifacts (all returned keys, except those starting with '_')
            out_map: dict[str, str] = {}
            for out_name, out_value in step_output.items():
                if out_name.startswith("_"):
                    continue
                path = f"{step.name}/{out_name}"
                out_key = build_artifact_key(ctx.run_id, ctx.entity_key, path)
                logical_address = path
                created_at = datetime.now(timezone.utc)  # noqa: UP017
                content_type = _content_type_for_value(out_value)
                _persist_output(
                    ctx.store,
                    out_key,
                    out_value,
                    created_at=created_at,
                )
                if ctx.index is not None:
                    ctx.index.record(
                        run_id=ctx.run_id,
                        artifact_key=out_key,
                        logical_address=logical_address,
                        entity_key=ctx.entity_key,
                        created_at=created_at,
                        content_type=content_type,
                    )
                out_map[out_name] = out_key
                info.artifacts_written.append(out_key)
                ctx.bindings[f"{step.name}/{out_name}"] = out_key

            step_info.outputs = out_map
            step_info.status = "succeeded"

        primary_artifact_path = None
        if info.steps:
            last_step = info.steps[-1]
            if last_step.outputs:
                first_out = next(iter(last_step.outputs.keys()))
                primary_artifact_path = f"{last_step.name}/{first_out}"

        _upsert_entity_run(
            ctx.store,
            ctx.run_id,
            ctx.entity_key,
            "succeeded",
            artifact_path=primary_artifact_path,
            run_config_json=ctx.run_config_json,
            entity_config_json=ctx.entity_config_json,
        )
        info.status = "succeeded"
        return info

    except Exception as e:
        info.status = "failed"
        msg = f"{type(e).__name__}: {e}"
        info.errors.append(msg)
        if info.steps:
            info.steps[-1].status = "failed"
            info.steps[-1].error = msg
        primary_artifact_path = None
        if info.steps:
            last_step = info.steps[-1]
            if last_step.outputs:
                first_out = next(iter(last_step.outputs.keys()))
                primary_artifact_path = f"{last_step.name}/{first_out}"
        _upsert_entity_run(
            ctx.store,
            ctx.run_id,
            ctx.entity_key,
            "failed",
            artifact_path=primary_artifact_path,
            run_config_json=ctx.run_config_json,
            entity_config_json=ctx.entity_config_json,
        )
        return info
