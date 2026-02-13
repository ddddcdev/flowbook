"""
Routes: GET /artifacts, GET /artifacts/{key}, GET /artifacts/{key}/raw

Operational endpoints for browsing run results.
"""

from __future__ import annotations

import io
import json
from typing import Any

from fastapi import APIRouter, Response

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


def _raw_response(key: str, val: Any) -> Response:
    """Build Response with appropriate Content-Type and body."""
    if isinstance(val, (dict, list)):
        return Response(
            content=json.dumps(val, ensure_ascii=False),
            media_type="application/json",
        )
    if isinstance(val, bytes):
        return Response(content=val, media_type="application/octet-stream")
    # DataFrame (avoid top-level pandas import)
    if type(val).__name__ == "DataFrame":
        buf = io.BytesIO()
        val.to_parquet(buf, engine="pyarrow", index=True)
        return Response(
            content=buf.getvalue(),
            media_type="application/x-parquet",
        )
    # Fallback: JSON-serialize
    return Response(
        content=json.dumps(val, ensure_ascii=False),
        media_type="application/json",
    )


@router.get("/{key:path}/raw")
def get_artifact_raw(key: str) -> Response:
    """Return raw artifact bytes/body with Content-Type. For downloads and head."""
    engine = get_engine()
    try:
        val = engine.store.get_any(key)
        return _raw_response(key, val)
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
