"""
run:
- Executes a Pipeline sequentially.
- Step.inputs are logical names; resolution is done via RunContext.bindings:
    logical -> artifact_key -> store.get -> value passed to op.
- Ops MUST NOT assume artifact keys; they receive values.
"""

from __future__ import annotations

import pandas as pd

from flowbook.runtime.context import RunContext
from flowbook.runtime.types import Pipeline, RunInfo, StepRunInfo


def _resolve_inputs(step, ctx):
    resolved = {}
    for param, logical in step.inputs.items():
        if logical not in ctx.bindings:
            raise KeyError(f"BindingNotFound: {logical}")
        artifact_key = ctx.bindings[logical]
        resolved[param] = ctx.store.get(artifact_key)
    return resolved


def _persist_output(store, out_key: str, value) -> None:
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
