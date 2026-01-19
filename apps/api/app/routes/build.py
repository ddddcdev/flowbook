"""
Route: /build
- Build a pipeline from profile and config
"""

from __future__ import annotations

from fastapi import APIRouter

from adapters.fastapi.contracts import BuildRequest, BuildResponse
from adapters.fastapi.errors import to_http_error
from adapters.fastapi.mapping import build_to_pipeline
from apps.api.app.deps import STATE, ensure_initialized, new_pipeline_id

"""
Route: /build
- Build a pipeline from profile and config
"""

router = APIRouter()


@router.post("/build", response_model=BuildResponse)
def build_route(req: BuildRequest) -> BuildResponse:
    ensure_initialized()
    try:
        pipeline = build_to_pipeline(req.profile, req.config)
        pid = new_pipeline_id()
        STATE.pipelines[pid] = pipeline
        return BuildResponse(pipeline_id=pid)
    except Exception as e:
        raise to_http_error(e)
