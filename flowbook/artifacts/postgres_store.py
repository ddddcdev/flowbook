from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import pandas as pd
from sqlalchemy import (
    JSON,
    Column,
    LargeBinary,
    MetaData,
    Table,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

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
class PostgresArtifactsStore:
    database_url: str

    def __post_init__(self) -> None:
        self.engine = create_engine(self.database_url, future=True)

    def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        meta: Optional[Mapping[str, Any]] = None,
    ) -> None:
        meta = dict(meta or {})
        stmt = (
            pg_insert(artifacts)
            .values(
                artifact_key=key,
                content_type=content_type,
                bytes=data,
                json=None,
                meta=meta,
            )
            .on_conflict_do_update(
                index_elements=[artifacts.c.artifact_key],
                set_={
                    "content_type": content_type,
                    "bytes": data,
                    "json": None,
                    "meta": meta,
                },
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def get_bytes(self, key: str) -> bytes:
        stmt = select(artifacts.c.bytes).where(artifacts.c.artifact_key == key)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).one()
        b = row[0]
        if b is None:
            raise KeyError(key)
        return b

    def put_json(
        self, key: str, obj: Any, *, meta: Optional[Mapping[str, Any]] = None
    ) -> None:
        meta = dict(meta or {})
        stmt = (
            pg_insert(artifacts)
            .values(
                artifact_key=key,
                content_type="application/json",
                bytes=None,
                json=obj,
                meta=meta,
            )
            .on_conflict_do_update(
                index_elements=[artifacts.c.artifact_key],
                set_={
                    "content_type": "application/json",
                    "bytes": None,
                    "json": obj,
                    "meta": meta,
                },
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def get_json(self, key: str) -> Any:
        stmt = select(artifacts.c.json).where(artifacts.c.artifact_key == key)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).one()
        j = row[0]
        if j is None:
            raise KeyError(key)
        return j

    def put_df(
        self, key: str, df: pd.DataFrame, *, meta: Optional[Mapping[str, Any]] = None
    ) -> None:
        self.put_bytes(
            key,
            df_to_parquet_bytes(df),
            content_type="application/x-parquet",
            meta=meta,
        )

    def get_df(self, key: str) -> pd.DataFrame:
        return parquet_bytes_to_df(self.get_bytes(key))
