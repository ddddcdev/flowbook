"""
FastAPI contracts:
- Request/response schemas
Rule:
- Do not leak flowbook internal types
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


"""
FastAPI contracts:
- Request/response schemas
Rule:
- Do not leak flowbook internal types
"""


class InspectRequest(BaseModel):
    input: Any


class InspectResponse(BaseModel):
    profile: dict[str, Any]


class BuildRequest(BaseModel):
    profile: dict[str, Any]
    config: dict[str, Any]


class BuildResponse(BaseModel):
    pipeline_id: str


class RunRequest(BaseModel):
    pipeline_id: str
    ctx: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    run_info: dict[str, Any]


class ArtifactsListResponse(BaseModel):
    keys: list[str]


class ArtifactGetResponse(BaseModel):
    key: str
    value: Any
