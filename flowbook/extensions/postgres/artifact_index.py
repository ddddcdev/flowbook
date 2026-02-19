"""Postgres-backed artifact index for list_index and latest_per_logical queries.

Uses the artifacts table directly (run_id, logical_address, namespace_prefix, created_at
are stored with each artifact). record() is a no-op since metadata is written by
PostgresArtifactsStore.put/put_bytes/put_df.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import create_engine, select, text

from flowbook.core.artifacts.index import ArtifactIndex, IndexRow

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
        namespace_prefix: str,
        created_at: datetime,
        content_type: str,
    ) -> None:
        # No-op: metadata is stored with artifacts by PostgresArtifactsStore.
        pass

    def list_index(
        self,
        namespace_prefix: str,
        limit: int = 200,
        order: Literal["desc", "asc"] = "desc",
    ) -> list[IndexRow]:
        order_clause = (
            artifacts.c.created_at.desc()
            if order == "desc"
            else artifacts.c.created_at.asc()
        )
        stmt = (
            select(
                artifacts.c.run_id,
                artifacts.c.artifact_key,
                artifacts.c.logical_address,
                artifacts.c.namespace_prefix,
                artifacts.c.created_at,
                artifacts.c.content_type,
            )
            .where(
                artifacts.c.namespace_prefix == namespace_prefix,
                artifacts.c.run_id.isnot(None),
                artifacts.c.logical_address.isnot(None),
            )
            .order_by(order_clause)
            .limit(limit)
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
        return [
            IndexRow(
                run_id=r[0],
                artifact_key=r[1],
                logical_address=r[2],
                namespace_prefix=r[3],
                created_at=r[4],
                content_type=r[5],
            )
            for r in rows
        ]

    def latest_per_logical(
        self,
        namespace_prefix: str,
        limit: int = 200,
    ) -> list[IndexRow]:
        stmt = text(
            """
            SELECT run_id, artifact_key, logical_address, namespace_prefix, created_at, content_type
            FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY logical_address ORDER BY created_at DESC
                ) AS rn
                FROM artifacts
                WHERE namespace_prefix = :prefix
                  AND run_id IS NOT NULL
                  AND logical_address IS NOT NULL
            ) sub
            WHERE rn = 1
            ORDER BY created_at DESC
            LIMIT :lim
            """
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt, {"prefix": namespace_prefix, "lim": limit}).fetchall()
        return [
            IndexRow(
                run_id=r[0],
                artifact_key=r[1],
                logical_address=r[2],
                namespace_prefix=r[3],
                created_at=r[4],
                content_type=r[5],
            )
            for r in rows
        ]
