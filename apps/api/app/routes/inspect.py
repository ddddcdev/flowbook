"""
Route: /inspect
- Accept input and return a profile
"""

from __future__ import annotations

from fastapi import APIRouter

from adapters.fastapi.contracts import InspectRequest, InspectResponse
from adapters.fastapi.errors import to_http_error
from adapters.fastapi.mapping import inspect_to_profile
from apps.api.app.deps import ensure_initialized

"""
Route: /inspect
- Accept input and return a profile
"""

router = APIRouter()


@router.post("/inspect", response_model=InspectResponse)
def inspect_route(req: InspectRequest) -> InspectResponse:
    ensure_initialized()
    try:
        profile = inspect_to_profile(req.input)
        return InspectResponse(profile=profile)
    except Exception as e:
        raise to_http_error(e)
