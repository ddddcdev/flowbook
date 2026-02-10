from __future__ import annotations

from typing import Any

from flowbook.runtime.build import build as fb_build
from flowbook.runtime.context import RunContext
from flowbook.runtime.run import run as fb_run
from flowbook.runtime.types import Pipeline, RunInfo


def build_pipeline(config: dict[str, Any]) -> Pipeline:
    return fb_build(config)


def run_pipeline(pipeline: Pipeline, ctx: RunContext) -> RunInfo:
    return fb_run(pipeline, ctx)


def run_info_dict(info: RunInfo) -> dict[str, Any]:
    return {
        "run_id": info.run_id,
        "status": info.status,
        "steps": [
            {
                "name": s.name,
                "status": s.status,
                "inputs": dict(s.inputs),
                "outputs": dict(s.outputs),
                "error": s.error,
            }
            for s in info.steps
        ],
        "artifacts_written": list(info.artifacts_written),
        "errors": list(info.errors),
    }
