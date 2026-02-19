"""
Routes: GET /artifacts, GET /artifacts/{key}, GET /artifacts/{key}/raw, as_excel.

Operational endpoints for browsing run results.
"""

from __future__ import annotations

import io
import json
from typing import Any

from fastapi import APIRouter, Response

from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import (
    ArtifactEntry,
    ArtifactGetResponse,
    ArtifactsListResponse,
)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _key_parts(key: str) -> tuple[str, str]:
    """Return (run_id, step_output). run_id is first path segment."""
    parts = key.split("/", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (key, "")


@router.get("", response_model=ArtifactsListResponse)
def list_artifacts(prefix: str | None = None) -> ArtifactsListResponse:
    engine = get_engine()
    try:
        keys = engine.store.list(prefix=prefix)
        entries = [
            ArtifactEntry(
                key=k,
                run_id=_key_parts(k)[0],
                step_output=_key_parts(k)[1],
            )
            for k in keys
        ]
        return ArtifactsListResponse(keys=keys, entries=entries)
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


@router.get("/{key:path}/as_excel")
def get_artifact_as_excel(key: str) -> Response:
    """Return DataFrame artifact as xlsx. Use for import (read/df) download."""
    import pandas as pd

    engine = get_engine()
    try:
        val = engine.store.get_any(key)
        if not isinstance(val, pd.DataFrame):
            raise ValueError(f"Artifact {key} is not a DataFrame; use /raw for other types")
        buf = io.BytesIO()
        val.to_excel(buf, sheet_name="out", index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=imported.xlsx"},
        )
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
