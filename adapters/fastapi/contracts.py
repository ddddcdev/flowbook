"""
FastAPI contracts:
- Request/response schemas
Rule:
- Do not leak flowbook internal types
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InspectRequest(BaseModel):
    input: Any


class InspectResponse(BaseModel):
    profile: dict[str, Any]


class BuildRequest(BaseModel):
    """
    Request to build a pipeline. Merged into a single pipeline_config as:
    pipeline_config = {**(profile or {}), **(config or {})}; config overrides profile.

    - profile: Optional. Environment- or run-specific overrides (e.g. default bindings).
      Applied first; may be overridden by config.
    - config: Pipeline definition. Should contain at least 'steps'. Merged after profile
      so config wins on overlapping keys. Required for a non-empty pipeline.
    """

    profile: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


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
