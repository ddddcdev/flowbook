"""
run:
- Executes a Pipeline sequentially.
- Step.inputs are logical names; resolution is done via RunContext.bindings:
    logical -> artifact_key -> store.get -> value passed to op.
- Ops MUST NOT assume artifact keys; they receive values.
- Preflight: missing bindings, unregistered op, PortSpec (required/surplus).
"""

from __future__ import annotations

import pandas as pd

from flowbook.artifacts.store import JsonValue
from flowbook.registry.registry import UnknownOp
from flowbook.runtime.context import RunContext
from flowbook.runtime.store import RunStore
from flowbook.runtime.types import Pipeline, RunInfo, Step, StepRunInfo


def _validate_step_contracts(pipeline: Pipeline, ctx: RunContext) -> None:
    """
    Preflight: every step has a registered op; if op has a contract (non-empty port_spec),
    step inputs satisfy required and have no surplus keys.
    Raises RuntimeError with run_id, step name, and missing/surplus keys.
    """
    for step in pipeline.steps:
        try:
            op = ctx.registry.get(step.op)
        except UnknownOp as e:
            raise RuntimeError(
                f"unregistered op in run_id='{ctx.run_id}': step '{step.name}' op '{e.args[0]}'"
            ) from e

        spec = op.port_spec()
        if not spec.allowed_keys():
            continue
        param_keys = set(step.inputs.keys())
        required_set = set(spec.required)
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


def _validate_required_inputs(pipeline: Pipeline, ctx: RunContext) -> None:
    """
    Preflight validation: ensure all referenced input keys exist in bindings.

    Fails fast if any step references a logical input key that is not in the
    run input space (ctx.bindings).

    Raises:
        RuntimeError: If any required inputs are missing, with details about
                     run_id, missing keys, and steps that referenced them.
    """
    referenced_keys = set()
    step_refs = {}  # key -> list of step names that reference it

    for step in pipeline.steps:
        for logical_name in step.inputs.values():
            referenced_keys.add(logical_name)
            if logical_name not in step_refs:
                step_refs[logical_name] = []
            step_refs[logical_name].append(step.name)

    missing_keys = sorted(k for k in referenced_keys if k not in ctx.bindings)

    if missing_keys:
        missing_details = ", ".join(f"'{k}'" for k in missing_keys)
        step_details = " | ".join(
            f"'{k}' used by {{{', '.join(step_refs[k])}}}" for k in missing_keys
        )
        raise RuntimeError(
            f"missing required input keys in run_id='{ctx.run_id}': {missing_details} "
            f"({step_details})"
        )


def _resolve_inputs(step: Step, ctx: RunContext) -> dict[str, object]:
    resolved: dict[str, object] = {}
    for param, logical in step.inputs.items():
        if logical not in ctx.bindings:
            raise KeyError(f"BindingNotFound: {logical}")
        artifact_key = ctx.bindings[logical]
        resolved[param] = ctx.store.get(artifact_key)
    return resolved


def _persist_output(store: RunStore, out_key: str, value: JsonValue | bytes | pd.DataFrame) -> None:
    if isinstance(value, bytes):
        store.put_bytes(out_key, value)
        return
    if isinstance(value, pd.DataFrame):
        store.put_df(out_key, value)
        return
    store.put(out_key, value)


def run(pipeline: Pipeline, ctx: RunContext) -> RunInfo:
    info = RunInfo(run_id=ctx.run_id, status="running")

    try:
        _validate_step_contracts(pipeline, ctx)
        _validate_required_inputs(pipeline, ctx)

        for step in pipeline.steps:
            s_info = StepRunInfo(
                name=step.name,
                status="running",
                inputs=dict(step.inputs),
            )
            info.steps.append(s_info)

            # Resolve inputs: artifact key -> value
            resolved_inputs = _resolve_inputs(step, ctx)

            # Resolve op
            op_fn = ctx.registry.get(step.op)

            # Execute op (pure function expectation; artifacts writing done here)
            produced = op_fn(resolved_inputs, ctx.store)
            if not isinstance(produced, dict):
                raise TypeError(
                    f"Step '{step.name}' must return dict[str, Any]; got {type(produced).__name__}"
                )

            # Persist outputs to artifacts (all returned keys, except those starting with '_')
            out_map: dict[str, str] = {}
            for out_name, out_value in produced.items():
                if out_name.startswith("_"):
                    continue
                out_key = f"artifact:{ctx.run_id}/{step.name}/{out_name}"
                _persist_output(ctx.store, out_key, out_value)
                out_map[out_name] = out_key
                info.artifacts_written.append(out_key)

            s_info.outputs = out_map
            s_info.status = "succeeded"

        info.status = "succeeded"
        return info

    except Exception as e:
        info.status = "failed"
        msg = f"{type(e).__name__}: {e}"
        info.errors.append(msg)
        if info.steps:
            info.steps[-1].status = "failed"
            info.steps[-1].error = msg
        return info
