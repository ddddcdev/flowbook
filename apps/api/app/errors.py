"""
Map flowbook exceptions to HTTP errors.

DoD: failure responses always include run_id (if available) + reason.
"""

from __future__ import annotations

from fastapi import HTTPException

from flowbook.artifacts.store import ArtifactNotFound
from flowbook.registry.registry import UnknownOp


def to_http_error(e: Exception, *, run_id: str | None = None) -> HTTPException:
    detail: dict[str, str | None] = {"run_id": run_id}

    if isinstance(e, ArtifactNotFound):
        detail["reason"] = f"artifact not found: {e.args[0]}"
        return HTTPException(status_code=404, detail=detail)

    if isinstance(e, UnknownOp):
        detail["reason"] = f"unknown op: {e.args[0]}"
        return HTTPException(status_code=400, detail=detail)

    if isinstance(e, KeyError):
        detail["reason"] = f"key error: {e}"
        return HTTPException(status_code=400, detail=detail)

    if isinstance(e, ValueError):
        detail["reason"] = str(e)
        return HTTPException(status_code=400, detail=detail)

    if isinstance(e, RuntimeError):
        detail["reason"] = str(e)
        return HTTPException(status_code=400, detail=detail)

    detail["reason"] = "internal error"
    return HTTPException(status_code=500, detail=detail)
