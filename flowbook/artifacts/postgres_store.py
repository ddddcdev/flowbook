from __future__ import annotations

import io
import json
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import (
    JSON,
    Column,
    LargeBinary,
    MetaData,
    Table,
    Text,
    create_engine,
    delete,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from flowbook.artifacts.store import ArtifactNotFound, ArtifactsStore, JsonValue

metadata = MetaData()

artifacts = Table(
    "artifacts",
    metadata,
    Column("artifact_key", Text, primary_key=True),
    Column("content_type", Text, nullable=False),
    Column("codec", Text, nullable=False, server_default="none"),
    Column("bytes", LargeBinary, nullable=True),
    Column("json", JSON, nullable=True),
    Column("meta", JSON, nullable=False, server_default="{}"),
)


def df_to_parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, engine="pyarrow", index=True)
    return buf.getvalue()


def parquet_bytes_to_df(b: bytes) -> pd.DataFrame:
    buf = io.BytesIO(b)
    return pd.read_parquet(buf, engine="pyarrow")


@dataclass
class PostgresArtifactsStore(ArtifactsStore):
    database_url: str

    def __post_init__(self) -> None:
        self.engine = create_engine(self.database_url, future=True)

    # ---- Protocol: JSON only ----
    def put(self, key: str, value: JsonValue) -> str:
        # JSON serializable 固定（暗黙エンコード禁止）
        try:
            json.dumps(value)
        except TypeError as e:
            raise TypeError(f"put expects JSON-serializable value: key={key}") from e

        stmt = (
            pg_insert(artifacts)
            .values(
                artifact_key=key,
                content_type="application/json",
                codec="none",
                bytes=None,
                json=value,
                meta={},
            )
            .on_conflict_do_update(
                index_elements=[artifacts.c.artifact_key],
                set_={
                    "content_type": "application/json",
                    "codec": "none",
                    "bytes": None,
                    "json": value,
                    "meta": {},
                },
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        return key

    def get(self, key: str) -> JsonValue:
        stmt = select(artifacts.c.json).where(artifacts.c.artifact_key == key)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).one_or_none()
        if row is None or row[0] is None:
            raise ArtifactNotFound(key)
        return row[0]

    def get_dict(self, key: str) -> dict[str, Any]:
        v = self.get(key)
        if not isinstance(v, dict):
            raise TypeError(f"artifact is not a dict: {key}")
        return v

    def list(self, prefix: str | None = None) -> list[str]:
        stmt = select(artifacts.c.artifact_key)
        if prefix is not None:
            stmt = stmt.where(artifacts.c.artifact_key.like(f"{prefix}%"))
        stmt = stmt.order_by(artifacts.c.artifact_key)

        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        return [r[0] for r in rows]

    # ---- Protocol: bytes ----
    def put_bytes(self, key: str, data: bytes) -> str:
        stmt = (
            pg_insert(artifacts)
            .values(
                artifact_key=key,
                content_type="application/octet-stream",
                codec="none",
                bytes=data,
                json=None,
                meta={},
            )
            .on_conflict_do_update(
                index_elements=[artifacts.c.artifact_key],
                set_={
                    "content_type": "application/octet-stream",
                    "codec": "none",
                    "bytes": data,
                    "json": None,
                    "meta": {},
                },
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        return key

    def get_bytes(self, key: str) -> bytes:
        stmt = select(artifacts.c.bytes).where(artifacts.c.artifact_key == key)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).one_or_none()
        if row is None or row[0] is None:
            raise ArtifactNotFound(key)
        return row[0]

    # ---- Protocol: df ----
    def put_df(self, key: str, df: pd.DataFrame) -> str:
        b = df_to_parquet_bytes(df)

        meta = {
            "row_count": int(df.shape[0]),
            "col_count": int(df.shape[1]),
            "columns": [str(c) for c in df.columns.tolist()],
            "schema": {str(c): str(df.dtypes[c]) for c in df.columns},
        }

        stmt = (
            pg_insert(artifacts)
            .values(
                artifact_key=key,
                content_type="application/x-parquet",
                codec="parquet",
                bytes=b,
                json=None,
                meta=meta,
            )
            .on_conflict_do_update(
                index_elements=[artifacts.c.artifact_key],
                set_={
                    "content_type": "application/x-parquet",
                    "codec": "parquet",
                    "bytes": b,
                    "json": None,
                    "meta": meta,
                },
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        return key

    def get_df(self, key: str) -> pd.DataFrame:
        return parquet_bytes_to_df(self.get_bytes(key))

    def delete_run(self, run_id: str) -> int:
        if not run_id:
            raise ValueError("run_id must be non-empty")
        stmt = delete(artifacts).where(artifacts.c.artifact_key.like(f"{run_id}/%"))
        with self.engine.begin() as conn:
            res = conn.execute(stmt)
        return int(res.rowcount or 0)
