"""
run:
- Execute a pipeline in order and return run_info
- All data products must go to artifacts
- Return value contains execution info only
Not included:
- Persistence
- Async, retries, or distributed execution
"""

from __future__ import annotations

from flowbook.runtime.context import RunContext
from flowbook.runtime.types import Pipeline, RunInfo, StepRunInfo


"""
run:
- Execute a pipeline in order and return run_info
- All data products must go to artifacts
- Return value contains execution info only
Not included:
- Persistence
- Async, retries, or distributed execution
"""


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
            resolved_inputs: dict[str, object] = {}
            for k, artifact_key in step.inputs.items():
                resolved_inputs[k] = ctx.store.get(artifact_key)

            # Resolve op
            op_fn = ctx.registry.get(step.op)

            # Execute op (pure function expectation; artifacts writing done here)
            produced = op_fn(resolved_inputs, ctx.store) or {}

            # Persist outputs to artifacts
            out_map: dict[str, str] = {}
            for out_name in step.outputs:
                out_key = f"artifact:{ctx.run_id}/{step.name}/{out_name}"
                ctx.store.put(out_key, produced.get(out_name))
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
