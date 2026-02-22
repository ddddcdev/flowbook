"""Artifact index: record and query by entity_key for tenant 'latest' use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable


@dataclass
class IndexRow:
    """One row in the artifact index."""

    run_id: str
    artifact_key: str
    logical_address: str
    entity_key: str
    created_at: datetime
    content_type: str


@runtime_checkable
class ArtifactIndex(Protocol):
    """Protocol for recording and querying artifact index."""

    def record(
        self,
        run_id: str,
        artifact_key: str,
        logical_address: str,
        entity_key: str,
        created_at: datetime,
        content_type: str,
    ) -> None: ...

    def list_index(
        self,
        entity_key: str,
        limit: int = 200,
        order: Literal["desc", "asc"] = "desc",
    ) -> list[IndexRow]: ...

    def latest_per_logical(
        self,
        entity_key: str,
        limit: int = 200,
    ) -> list[IndexRow]: ...
