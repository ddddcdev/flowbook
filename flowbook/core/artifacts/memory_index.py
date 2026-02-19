"""In-memory artifact index for tests and single-process use."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from flowbook.core.artifacts.index import ArtifactIndex, IndexRow


class InMemoryArtifactIndex(ArtifactIndex):
    """In-memory artifact index: list + sort; latest_per_logical via distinct on logical_address."""

    def __init__(self) -> None:
        self._rows: list[IndexRow] = []

    def record(
        self,
        run_id: str,
        artifact_key: str,
        logical_address: str,
        namespace_prefix: str,
        created_at: datetime,
        content_type: str,
    ) -> None:
        self._rows.append(
            IndexRow(
                run_id=run_id,
                artifact_key=artifact_key,
                logical_address=logical_address,
                namespace_prefix=namespace_prefix,
                created_at=created_at,
                content_type=content_type,
            )
        )

    def list_index(
        self,
        namespace_prefix: str,
        limit: int = 200,
        order: Literal["desc", "asc"] = "desc",
    ) -> list[IndexRow]:
        filtered = [r for r in self._rows if r.namespace_prefix == namespace_prefix]
        filtered.sort(key=lambda r: r.created_at, reverse=(order == "desc"))
        return filtered[:limit]

    def latest_per_logical(
        self,
        namespace_prefix: str,
        limit: int = 200,
    ) -> list[IndexRow]:
        filtered = [r for r in self._rows if r.namespace_prefix == namespace_prefix]
        filtered.sort(key=lambda r: (r.logical_address, r.created_at), reverse=True)
        seen: set[str] = set()
        result: list[IndexRow] = []
        for r in filtered:
            if r.logical_address not in seen:
                seen.add(r.logical_address)
                result.append(r)
                if len(result) >= limit:
                    break
        result.sort(key=lambda r: r.created_at, reverse=True)
        return result
