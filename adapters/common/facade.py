from __future__ import annotations

from typing import Any

from flowbook.runtime.build import build as fb_build
from flowbook.runtime.context import RunContext
from flowbook.runtime.run import run as fb_run
from flowbook.runtime.types import Pipeline, RunInfo


def build_pipeline(pipeline_config: dict[str, Any]) -> Pipeline:
    return fb_build(pipeline_config)


def run_pipeline(pipeline: Pipeline, ctx: RunContext) -> RunInfo:
    return fb_run(pipeline, ctx)


def run_info_dict(info: RunInfo) -> dict[str, Any]:
    return {
        "run_id": info.run_id,
        "status": info.status,
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "inputs": dict(step.inputs),
                "outputs": dict(step.outputs),
                "error": step.error,
            }
            for step in info.steps
        ],
        "artifacts_written": list(info.artifacts_written),
        "errors": list(info.errors),
    }
