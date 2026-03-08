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
    """Form parameters for POST /import (file is separate)."""

    plan_name: str
    inputs: str = "{}"


class RunResponse(BaseModel):
    run_id: str
    status: str
    artifacts_written: list[str] = []
    errors: list[str] = []
    steps: list[dict[str, Any]] = []
    warnings: list[str] = []


# ---- /export ----


class ExportRequest(BaseModel):
    plan_name: str
    bindings: dict[str, str] = {}
    inputs: dict[str, Any] = {}


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


# ---- /chat ----


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str
    messages: list[ChatMessage] = []
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    response: str


# ---- /configs ----


class ConfigEntry(BaseModel):
    config_type: str
    config_name: str


class ConfigsListResponse(BaseModel):
    configs: list[ConfigEntry] = []


class ConfigGetResponse(BaseModel):
    config_type: str
    config_name: str
    spec: dict[str, Any]
    spec_text: str | None = None


class ConfigCreateRequest(BaseModel):
    """Body for POST /configs."""

    config_type: str
    config_name: str
    spec: dict[str, Any]
    spec_text: str | None = None


class ConfigUpdateRequest(BaseModel):
    """Body for PUT /configs/{config_type}/{config_name}."""

    spec: dict[str, Any]
    spec_text: str | None = None


class ConfigAiEditRequest(BaseModel):
    """Body for POST /configs/ai-edit. spec_text = full spec (user edits and maintains)."""

    config_type: str
    config_name: str
    spec_text: str
    """Full spec text. AI interprets and generates spec. Stored as-is."""
    inputs: dict[str, Any] = {}
    """Optional plan/run context (JSON). Passed to AI. Plan-specific."""


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


# ---- /entities ----


class EntityEntry(BaseModel):
    entity_key: str
    meta: dict[str, Any] = {}
    created_at: str | None = None
    updated_at: str | None = None


class EntitiesListResponse(BaseModel):
    entries: list[EntityEntry] = []


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
    meta: dict = {}
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
    meta: dict = {}
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
    meta: dict = {}
    created_at: str | None = None
    updated_at: str | None = None
