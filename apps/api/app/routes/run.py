"""
Route: /run
- Execute a pipeline and return run_info
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from adapters.fastapi.contracts import RunRequest, RunResponse
from adapters.fastapi.errors import to_http_error
from adapters.fastapi.mapping import run_info_to_dict, run_pipeline
from apps.api.app.deps import STATE, create_run_context, ensure_initialized

"""
Route: /run
- Execute a pipeline and return run_info
"""

router = APIRouter()


@router.post("/run", response_model=RunResponse)
def run_route(req: RunRequest) -> RunResponse:
    ensure_initialized()
    try:
        if req.pipeline_id not in STATE.pipelines:
            raise HTTPException(status_code=404, detail="pipeline_not_found")

        run_id = req.ctx.get("run_id")
        meta = req.ctx.get("meta")
        ctx = create_run_context(run_id=run_id, meta=meta)

        info = run_pipeline(STATE.pipelines[req.pipeline_id], ctx)
        return RunResponse(run_info=run_info_to_dict(info))
    except HTTPException:
        raise
    except Exception as e:
        raise to_http_error(e)
