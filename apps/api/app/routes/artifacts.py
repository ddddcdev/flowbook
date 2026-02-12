"""
Routes: GET /artifacts, GET /artifacts/{key}

Operational endpoints for browsing run results.
"""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.app.deps import get_engine
from apps.api.app.errors import to_http_error
from apps.api.app.schemas import ArtifactGetResponse, ArtifactsListResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("", response_model=ArtifactsListResponse)
def list_artifacts(prefix: str | None = None) -> ArtifactsListResponse:
    engine = get_engine()
    try:
        keys = engine.store.list(prefix=prefix)
        return ArtifactsListResponse(keys=keys)
    except Exception as e:
        raise to_http_error(e) from e


@router.get("/{key:path}", response_model=ArtifactGetResponse)
def get_artifact(key: str) -> ArtifactGetResponse:
    engine = get_engine()
    try:
        val = engine.store.get(key)
        return ArtifactGetResponse(key=key, value=val)
    except Exception as e:
        raise to_http_error(e) from e
