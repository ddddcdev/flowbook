"""
Route: /build
- Build a pipeline from profile and config
"""

from __future__ import annotations

from fastapi import APIRouter

from adapters.fastapi.contracts import BuildRequest, BuildResponse
from adapters.fastapi.errors import to_http_error
from adapters.fastapi.handlers import build_pipeline_handler as handle_build
from apps.api.app.deps import ensure_initialized

router = APIRouter()


@router.post("/build", response_model=BuildResponse)
def build_route(req: BuildRequest) -> BuildResponse:
    ensure_initialized()
    try:
        return handle_build(req)
    except Exception as e:
        raise to_http_error(e)
