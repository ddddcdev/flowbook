"""
Route: /artifacts
- List and fetch artifacts
Rule:
- Never return raw data via run_info
"""

from __future__ import annotations

from fastapi import APIRouter

from adapters.fastapi.contracts import ArtifactGetResponse, ArtifactsListResponse
from adapters.fastapi.errors import to_http_error
from apps.api.app.deps import STATE, ensure_initialized

"""
Route: /artifacts
- List and fetch artifacts
Rule:
- Never return raw data via run_info
"""

router = APIRouter()


@router.get("/artifacts", response_model=ArtifactsListResponse)
def list_artifacts_route() -> ArtifactsListResponse:
    ensure_initialized()
    try:
        return ArtifactsListResponse(keys=STATE.store.list())
    except Exception as e:
        raise to_http_error(e)


@router.get("/artifacts/{key:path}", response_model=ArtifactGetResponse)
def get_artifact_route(key: str) -> ArtifactGetResponse:
    ensure_initialized()
    try:
        val = STATE.store.get(key)
        return ArtifactGetResponse(key=key, value=val)
    except Exception as e:
        raise to_http_error(e)
