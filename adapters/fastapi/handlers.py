from __future__ import annotations

from fastapi import HTTPException

from adapters.common.facade import (
    build_pipeline,
    inspect_profile,
    run_info_dict,
    run_pipeline,
)
from adapters.fastapi.contracts import (
    BuildRequest,
    BuildResponse,
    InspectRequest,
    InspectResponse,
    RunRequest,
    RunResponse,
)
from apps.api.app.deps import STATE, create_run_context, new_pipeline_id


def inspect(req: InspectRequest) -> InspectResponse:
    profile = inspect_profile(req.input)
    return InspectResponse(profile=profile)


def build_pipeline_handler(req: BuildRequest) -> BuildResponse:
    pipeline = build_pipeline(req.profile, req.config)

    pid = new_pipeline_id()
    STATE.pipelines[pid] = pipeline

    return BuildResponse(pipeline_id=pid)


def run_pipeline_handler(req: RunRequest) -> RunResponse:
    if req.pipeline_id not in STATE.pipelines:
        raise HTTPException(status_code=404, detail="pipeline_not_found")

    run_id = req.ctx.get("run_id")
    meta = req.ctx.get("meta")
    ctx = create_run_context(run_id=run_id, meta=meta)

    info = run_pipeline(STATE.pipelines[req.pipeline_id], ctx)
    return RunResponse(run_info=run_info_dict(info))
