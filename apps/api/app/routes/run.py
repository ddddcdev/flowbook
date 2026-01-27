"""
Route: /run
- Execute a pipeline and return run_info
"""

from __future__ import annotations

from fastapi import APIRouter

from adapters.fastapi.contracts import RunRequest, RunResponse
from adapters.fastapi.errors import to_http_error
from adapters.fastapi.handlers import run_pipeline_handler as handle_run
from apps.api.app.deps import ensure_initialized

router = APIRouter()


@router.post("/run", response_model=RunResponse)
def run_route(req: RunRequest) -> RunResponse:
    ensure_initialized()
    try:
        return handle_run(req)
    except Exception as e:
        raise to_http_error(e) from e
