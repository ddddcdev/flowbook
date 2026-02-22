"""Postgres-backed artifact index for list_index and latest_per_logical queries.

Reads from artifacts table (composite PK: run_id, entity_key, artifact_path).
record() is a no-op since metadata is written by PostgresArtifactsStore.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import create_engine, select, text

from flowbook.core.artifacts.index import ArtifactIndex, IndexRow
from flowbook.core.artifacts.key_utils import build_artifact_key

from .artifacts_store import artifacts


class PostgresArtifactIndex(ArtifactIndex):
    """Postgres artifact index; reads from artifacts table (no separate index table)."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, future=True)

    def record(
        self,
        run_id: str,
        artifact_key: str,
        logical_address: str,
        entity_key: str,
        created_at: datetime,
        content_type: str,
    ) -> None:
        # No-op: metadata is stored with artifacts by PostgresArtifactsStore.
        pass

    def list_index(
        self,
        entity_key: str,
        limit: int = 200,
        order: Literal["desc", "asc"] = "desc",
    ) -> list[IndexRow]:
        order_clause = (
            artifacts.c.created_at.desc() if order == "desc" else artifacts.c.created_at.asc()
        )
        stmt = (
            select(
                artifacts.c.run_id,
                artifacts.c.entity_key,
                artifacts.c.artifact_path,
                artifacts.c.created_at,
                artifacts.c.content_type,
            )
            .where(artifacts.c.entity_key == entity_key)
            .order_by(order_clause)
            .limit(limit)
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
        return [
            IndexRow(
                run_id=r[0],
                artifact_key=build_artifact_key(r[0], r[1], r[2]),
                logical_address=r[2],
                entity_key=r[1],
                created_at=r[3],
                content_type=r[4],
            )
            for r in rows
        ]

    def latest_per_logical(
        self,
        entity_key: str,
        limit: int = 200,
    ) -> list[IndexRow]:
        stmt = text(
            """
            SELECT run_id, entity_key, artifact_path, created_at, content_type
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY artifact_path ORDER BY created_at DESC
                ) AS rn
                FROM artifacts
                WHERE entity_key = :ek
            ) sub
            WHERE rn = 1
            ORDER BY created_at DESC
            LIMIT :lim
            """
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt, {"ek": entity_key, "lim": limit}).fetchall()
        return [
            IndexRow(
                run_id=r[0],
                artifact_key=build_artifact_key(r[0], r[1], r[2]),
                logical_address=r[2],
                entity_key=r[1],
                created_at=r[3],
                content_type=r[4],
            )
            for r in rows
        ]
