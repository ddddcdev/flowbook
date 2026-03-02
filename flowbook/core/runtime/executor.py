"""
executor: Executes a Plan sequentially (run_id > exec(plan) > step hierarchy).

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
from flowbook.core.logging import get_logger
from flowbook.core.registry.registry import UnknownOp
from flowbook.core.runtime.context import RunContext
from flowbook.core.runtime.resolve import collect_refs_in_inputs, resolve_value
from flowbook.core.runtime.store import RunStore
from flowbook.core.runtime.types import Plan, RunInfo, Step, StepRunInfo

logger = get_logger(__name__)


class ResultArtifactsValidationError(RuntimeError):
    """Raised when result_artifacts path is not produced by any step."""


def _base_extra(
    run_id: str, entity_key: str, artifact_path: str | None = None
) -> dict[str, object]:
    """Build common extra dict. Omit artifact_path when None."""
    d: dict[str, object] = {"run_id": run_id, "entity_key": entity_key}
    if artifact_path is not None:
        d["artifact_path"] = artifact_path
    return d


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
    meta: dict | None = None,
) -> None:
    kwargs: dict = {}
    if created_at is not None:
        kwargs["created_at"] = created_at
    if meta:
        kwargs["meta"] = dict(meta)
    if isinstance(value, bytes):
        store.put_bytes(out_key, value, **kwargs)
        return
    # Lazy import to keep core import-safe (no pandas at import time).
    import pandas as pd

    if isinstance(value, pd.DataFrame):
        store.put_df(out_key, value, **kwargs)
        return
    store.put(out_key, cast(JsonValue, value), **kwargs)


def _result_artifacts_from_plan(plan: object, info: RunInfo) -> list[dict[str, str | None]] | None:
    """Build result_artifacts list from plan if declared. Validates paths exist in outputs."""
    ra = getattr(plan, "result_artifacts", None)
    if not ra:
        return None
    produced: set[str] = set()
    for s in info.steps:
        if s.outputs:
            for out_name in s.outputs:
                produced.add(f"{s.name}/{out_name}")
    out: list[dict[str, str | None]] = []
    for item in ra:
        path = (
            getattr(item, "path", None)
            if hasattr(item, "path")
            else (item.get("path") if isinstance(item, dict) else None)
        )
        label = (
            getattr(item, "label", None)
            if hasattr(item, "label")
            else (item.get("label") if isinstance(item, dict) else None)
        )
        if not path:
            continue
        if path not in produced:
            raise ResultArtifactsValidationError(
                f"result_artifacts path '{path}' not produced by any step. "
                f"Available: {sorted(produced)}"
            )
        out.append({"path": path, "label": label})
    return out if out else None


def _result_artifacts_from_last_step(info: RunInfo) -> list[dict[str, str | None]] | None:
    """Derive result_artifacts from last step's first output when plan has no result_artifacts."""
    if not info.steps:
        return None
    last = info.steps[-1]
    if not last.outputs:
        return None
    first_out = next(iter(last.outputs.keys()), None)
    if not first_out:
        return None
    return [{"path": f"{last.name}/{first_out}", "label": None}]


def _upsert_result(
    store: RunStore,
    run_id: str,
    entity_key: str,
    status: str,
    run_config_json: str | None = None,
    entity_config_json: str | None = None,
    result_artifacts: list[dict[str, str | None]] | None = None,
) -> None:
    """Upsert results if store supports it.
    result_artifacts: list of {path, label} for main results. Always set when run has outputs."""
    upsert = getattr(store, "upsert_result", None)
    if callable(upsert):
        upsert(
            run_id,
            entity_key,
            status,
            run_config_json=run_config_json,
            entity_config_json=entity_config_json,
            result_artifacts=result_artifacts,
        )


def execute_plan(plan: Plan, ctx: RunContext) -> RunInfo:
    """Execute a plan sequentially. Part of run_id > exec(plan) > step hierarchy."""
    plan_name = (ctx.meta or {}).get("plan_name") if ctx.meta else None
    step_names = [s.name for s in plan.steps]
    extra = {
        **_base_extra(ctx.run_id, ctx.entity_key),
        "plan_name": plan_name,
        "step_names": step_names,
    }
    logger.info("plan started", extra=extra)

    info = RunInfo(run_id=ctx.run_id, status="running")
    result_artifacts_list: list[dict[str, str | None]] | None = None
    _upsert_result(
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
            step_extra = {
                **_base_extra(ctx.run_id, ctx.entity_key),
                "step": step.name,
                "status": "running",
            }
            logger.debug("step started", extra=step_extra)

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
            step_meta = step_output.get("_meta")
            step_meta_dict = step_meta if isinstance(step_meta, dict) else None
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
                    meta=step_meta_dict,
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

            first_out = next(iter(out_map.keys()), None)
            primary_so_far = f"{step.name}/{first_out}" if first_out else None
            step_extra_done = {
                **_base_extra(ctx.run_id, ctx.entity_key, primary_so_far),
                "step": step.name,
                "status": "succeeded",
            }
            logger.debug("step completed", extra=step_extra_done)

        if plan.result_artifacts and info.steps:
            result_artifacts_list = _result_artifacts_from_plan(plan, info)
        if result_artifacts_list is None and info.steps:
            result_artifacts_list = _result_artifacts_from_last_step(info)

        _upsert_result(
            ctx.store,
            ctx.run_id,
            ctx.entity_key,
            "succeeded",
            run_config_json=ctx.run_config_json,
            entity_config_json=ctx.entity_config_json,
            result_artifacts=result_artifacts_list,
        )
        info.status = "succeeded"
        primary_path = result_artifacts_list[0]["path"] if result_artifacts_list else None
        exec_extra = {
            **_base_extra(ctx.run_id, ctx.entity_key, primary_path),
            "status": "succeeded",
        }
        logger.info("plan completed", extra=exec_extra)
        return info

    except ResultArtifactsValidationError:
        raise
    except Exception as e:
        info.status = "failed"
        msg = f"{type(e).__name__}: {e}"
        info.errors.append(msg)
        if info.steps:
            info.steps[-1].status = "failed"
            info.steps[-1].error = msg
        if plan.result_artifacts and info.steps:
            try:
                result_artifacts_list = _result_artifacts_from_plan(plan, info)
            except ResultArtifactsValidationError:
                pass
        if result_artifacts_list is None and info.steps:
            result_artifacts_list = _result_artifacts_from_last_step(info)

        _upsert_result(
            ctx.store,
            ctx.run_id,
            ctx.entity_key,
            "failed",
            run_config_json=ctx.run_config_json,
            entity_config_json=ctx.entity_config_json,
            result_artifacts=result_artifacts_list,
        )
        failed_step = info.steps[-1].name if info.steps else None
        primary_path = result_artifacts_list[0]["path"] if result_artifacts_list else None
        err_extra = {
            **_base_extra(ctx.run_id, ctx.entity_key, primary_path),
            "status": "failed",
            "error": msg,
            "step": failed_step,
        }
        logger.error("plan failed", extra=err_extra)
        return info
