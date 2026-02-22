"""
Routes: GET /artifacts, GET /artifacts/{key}, GET /artifacts/{key}/raw, as_excel.

Operational endpoints for browsing run results.
"""

from __future__ import annotations

import io
import json
import re
from typing import Any, cast

from fastapi import APIRouter, Query, Response

from flowbook.core.artifacts.store import ArtifactNotFound
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


def _filename_safe(name: str) -> str:
    """Remove path separators and unsafe chars from filename."""
    s = name.replace("/", "_").replace("\\", "_")
    return re.sub(r'[<>:"|?*\x00-\x1f]', "_", s) or "download"


def _download_filename(key: str, store: Any, content_type: str | None = None) -> str:
    """Get filename for download: meta.filename, else fallback from key/content_type."""
    get_meta = getattr(store, "get_artifact_meta", None)
    if callable(get_meta):
        meta_result = get_meta(key)
        if isinstance(meta_result, dict):
            artifact_meta = meta_result.get("meta")
            if isinstance(artifact_meta, dict):
                fn = artifact_meta.get("filename")
                if isinstance(fn, str):
                    return _filename_safe(fn)
    # Fallback: last segment of key + extension from content_type
    parts = key.split("/")
    base = parts[-1] if parts else "artifact"
    base = _filename_safe(base)
    if content_type and ("spreadsheet" in content_type or "excel" in content_type):
        return f"{base}.xlsx" if "." not in base else base
    if base == "bytes" or base == "artifact":
        return f"{base}.bin" if "." not in base else base
    return base


@router.get("", response_model=ArtifactsListResponse)
def list_artifacts(prefix: str | None = None) -> ArtifactsListResponse:
    engine = get_engine()
    try:
        store = engine.store
        list_with_meta = getattr(store, "list_with_meta", None)
        if callable(list_with_meta):
            items = cast(list[dict[str, Any]], list_with_meta(prefix=prefix))
            keys = [i["key"] for i in items]
            entries = [
                ArtifactEntry(
                    key=i["key"],
                    run_id=_key_parts(i["key"])[0],
                    step_output=_key_parts(i["key"])[1],
                    content_type=i.get("content_type"),
                    meta=i.get("meta"),
                    created_at=i.get("created_at"),
                )
                for i in items
            ]
        else:
            keys = store.list(prefix=prefix)
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


def _raw_response(
    key: str,
    val: Any,
    store: Any = None,
    download_filename: str | None = None,
) -> Response:
    """Build Response with appropriate Content-Type and body."""
    headers: dict[str, str] = {}
    if download_filename is None and store is not None:
        download_filename = _download_filename(key, store, "application/octet-stream")
    if isinstance(val, (dict, list)):
        return Response(
            content=json.dumps(val, ensure_ascii=False),
            media_type="application/json",
        )
    if isinstance(val, bytes):
        if download_filename:
            headers["Content-Disposition"] = f'attachment; filename="{download_filename}"'
        return Response(
            content=val,
            media_type="application/octet-stream",
            headers=headers if headers else None,
        )
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
        store = engine.store
        val = store.get_any(key)
        filename = _download_filename(key, store, "application/octet-stream")
        return _raw_response(key, val, download_filename=filename)
    except Exception as e:
        raise to_http_error(e) from e


@router.get("/{key:path}/as_excel")
def get_artifact_as_excel(key: str) -> Response:
    """Return DataFrame artifact as xlsx. Use for import (read/df) download."""
    import pandas as pd

    engine = get_engine()
    try:
        store = engine.store
        val = store.get_any(key)
        if not isinstance(val, pd.DataFrame):
            raise ValueError(f"Artifact {key} is not a DataFrame; use /raw for other types")
        filename = _download_filename(key, store, "application/vnd.ms-excel") or "imported.xlsx"
        buf = io.BytesIO()
        val.to_excel(buf, sheet_name="out", index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise to_http_error(e) from e


@router.get("/{key:path}", response_model=ArtifactGetResponse)
def get_artifact(
    key: str,
    meta_only: bool = Query(False, description="Return metadata only"),
) -> ArtifactGetResponse:
    engine = get_engine()
    try:
        store = engine.store
        get_artifact_meta = getattr(store, "get_artifact_meta", None)
        if meta_only and callable(get_artifact_meta):
            meta = get_artifact_meta(key)
            if meta is None:
                raise ArtifactNotFound(key)
            return ArtifactGetResponse(key=key, value=meta)
        val = engine.store.get(key)
        return ArtifactGetResponse(key=key, value=val)
    except Exception as e:
        raise to_http_error(e) from e
