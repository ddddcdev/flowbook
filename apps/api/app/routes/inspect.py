"""
Route: /inspect
- Accept input and return a profile
"""

from __future__ import annotations

from fastapi import APIRouter

from adapters.fastapi.contracts import InspectRequest, InspectResponse
from adapters.fastapi.errors import to_http_error
from adapters.fastapi.handlers import inspect as handle_inspect
from apps.api.app.deps import ensure_initialized

router = APIRouter()


@router.post("/inspect", response_model=InspectResponse)
def inspect_route(req: InspectRequest) -> InspectResponse:
    ensure_initialized()
    try:
        return handle_inspect(req)
    except Exception as e:
        raise to_http_error(e)
