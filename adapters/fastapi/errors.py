"""
FastAPI error mapping:
- Convert flowbook exceptions to HTTP errors
Rule:
- Error translation only
- No logging or auditing
"""

from __future__ import annotations

from fastapi import HTTPException

from flowbook.artifacts.store import ArtifactNotFound
from flowbook.registry.registry import UnknownOp

"""
FastAPI error mapping:
- Convert flowbook exceptions to HTTP errors
Rule:
- Error translation only
- No logging or auditing
"""


def to_http_error(e: Exception) -> HTTPException:
    if isinstance(e, ArtifactNotFound):
        return HTTPException(status_code=404, detail="artifact_not_found")
    if isinstance(e, UnknownOp):
        return HTTPException(status_code=400, detail="unknown_op")
    if isinstance(e, KeyError):
        return HTTPException(status_code=400, detail="bad_request")
    if isinstance(e, ValueError):
        return HTTPException(status_code=400, detail=str(e))
    return HTTPException(status_code=500, detail="internal_error")
