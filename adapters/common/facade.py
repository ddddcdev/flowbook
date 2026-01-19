from __future__ import annotations

from typing import Any

from flowbook.runtime.build import build as fb_build
from flowbook.runtime.inspect import inspect as fb_inspect
from flowbook.runtime.run import run as fb_run
from flowbook.runtime.types import RunInfo


def inspect_profile(input_obj: Any) -> dict[str, Any]:
    return fb_inspect(input_obj)


def build_pipeline(profile: dict[str, Any], config: dict[str, Any]):
    return fb_build(profile, config)


def run_pipeline(pipeline, ctx):
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
