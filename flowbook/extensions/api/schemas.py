"""
Pydantic request / response models.

Rule: Do not leak flowbook internal types into the HTTP surface.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# ---- common ----


class ErrorResponse(BaseModel):
    run_id: str | None = None
    reason: str


# ---- /inspect ----


class InspectResponse(BaseModel):
    run_id: str
    profile: dict[str, Any]


# ---- /import ----


class ImportRequest(BaseModel):
    """Additional parameters alongside the uploaded file."""

    template_name: str
    input_profile_name: str = "source"


class RunResponse(BaseModel):
    run_id: str
    status: str
    artifacts_written: list[str] = []
    errors: list[str] = []
    steps: list[dict[str, Any]] = []


# ---- /export ----


class ExportRequest(BaseModel):
    template_name: str
    bindings: dict[str, str] = {}


# ---- /artifacts ----


class ArtifactEntry(BaseModel):
    key: str
    run_id: str
    entity_key: str
    artifact_path: str
    content_type: str | None = None
    meta: dict[str, Any] | None = None
    created_at: str | None = None


class ArtifactsListResponse(BaseModel):
    keys: list[str]
    entries: list[ArtifactEntry] = []


class ArtifactGetResponse(BaseModel):
    key: str
    value: Any


# ---- /configs ----


class ConfigEntry(BaseModel):
    kind: str
    name: str


class ConfigsListResponse(BaseModel):
    configs: list[ConfigEntry] = []


class ConfigGetResponse(BaseModel):
    kind: str
    name: str
    spec: dict[str, Any]


# ---- /runs ----


class RunEntry(BaseModel):
    run_id: str
    status: str
    config_json: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RunsListResponse(BaseModel):
    entries: list[RunEntry] = []


class RunGetResponse(BaseModel):
    run_id: str
    status: str
    config_json: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ---- /results, /latest_results ----


class ResultArtifactEntry(BaseModel):
    """One main result artifact: path (step/key) and optional label for UI."""

    path: str
    label: str | None = None


class ResultEntry(BaseModel):
    run_id: str
    entity_key: str
    status: str
    result_artifacts: list[ResultArtifactEntry] | None = None
    config_json: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ResultsListResponse(BaseModel):
    entries: list[ResultEntry] = []


class ResultGetResponse(BaseModel):
    run_id: str
    entity_key: str
    status: str
    result_artifacts: list[ResultArtifactEntry] | None = None
    config_json: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class LatestResultsListResponse(BaseModel):
    entries: list[ResultEntry] = []


class LatestResultGetResponse(BaseModel):
    run_id: str
    entity_key: str
    status: str
    result_artifacts: list[ResultArtifactEntry] | None = None
    config_json: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
