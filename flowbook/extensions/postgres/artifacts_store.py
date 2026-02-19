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
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import insert as pg_insert

from flowbook.core.artifacts.store import ArtifactNotFound, ArtifactsStore, JsonValue

metadata = MetaData()

artifacts = Table(
    "artifacts",
    metadata,
    Column("artifact_key", Text, primary_key=True),
    Column("run_id", Text, nullable=True),
    Column("logical_address", Text, nullable=True),
    Column("namespace_prefix", Text, nullable=True),
    Column("created_at", TIMESTAMP(timezone=True), nullable=True),
    Column("content_type", Text, nullable=False),
    Column("codec", Text, nullable=False, server_default="none"),
    Column("bytes", LargeBinary, nullable=True),
    Column("json", JSON, nullable=True),
    Column("meta", JSON, nullable=False, server_default="{}"),
)

runs = Table(
    "runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("status", Text, nullable=False),
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    ),
    Column(
        "updated_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    ),
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

    def _meta_values(self, **kwargs: Any) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if "run_id" in kwargs:
            out["run_id"] = kwargs["run_id"]
        if "logical_address" in kwargs:
            out["logical_address"] = kwargs["logical_address"]
        if "namespace_prefix" in kwargs:
            out["namespace_prefix"] = kwargs["namespace_prefix"]
        if "created_at" in kwargs:
            out["created_at"] = kwargs["created_at"]
        return out

    # ---- Protocol: JSON only ----
    def put(self, key: str, value: JsonValue, **kwargs: Any) -> str:
        try:
            json.dumps(value)
        except TypeError as e:
            raise TypeError(f"put expects JSON-serializable value: key={key}") from e

        meta_vals = self._meta_values(**kwargs)
        vals = {
            "artifact_key": key,
            "content_type": "application/json",
            "codec": "none",
            "bytes": None,
            "json": value,
            "meta": {},
            **meta_vals,
        }
        set_cols = {k: v for k, v in vals.items() if k != "artifact_key"}

        stmt = (
            pg_insert(artifacts)
            .values(**vals)
            .on_conflict_do_update(
                index_elements=[artifacts.c.artifact_key],
                set_=set_cols,
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
    def put_bytes(self, key: str, data: bytes, **kwargs: Any) -> str:
        meta_vals = self._meta_values(**kwargs)
        vals = {
            "artifact_key": key,
            "content_type": "application/octet-stream",
            "codec": "none",
            "bytes": data,
            "json": None,
            "meta": {},
            **meta_vals,
        }
        set_cols = {k: v for k, v in vals.items() if k != "artifact_key"}
        stmt = (
            pg_insert(artifacts)
            .values(**vals)
            .on_conflict_do_update(
                index_elements=[artifacts.c.artifact_key],
                set_=set_cols,
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
    def put_df(self, key: str, df: pd.DataFrame, **kwargs: Any) -> str:
        b = df_to_parquet_bytes(df)

        meta = {
            "row_count": int(df.shape[0]),
            "col_count": int(df.shape[1]),
            "columns": [str(c) for c in df.columns.tolist()],
            "schema": {str(c): str(df.dtypes[c]) for c in df.columns},
        }

        meta_vals = self._meta_values(**kwargs)
        vals = {
            "artifact_key": key,
            "content_type": "application/x-parquet",
            "codec": "parquet",
            "bytes": b,
            "json": None,
            "meta": meta,
            **meta_vals,
        }
        set_cols = {k: v for k, v in vals.items() if k != "artifact_key"}
        stmt = (
            pg_insert(artifacts)
            .values(**vals)
            .on_conflict_do_update(
                index_elements=[artifacts.c.artifact_key],
                set_=set_cols,
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        return key

    def get_df(self, key: str) -> pd.DataFrame:
        return parquet_bytes_to_df(self.get_bytes(key))

    def get_any(self, key: str) -> JsonValue | bytes | pd.DataFrame:
        stmt = select(
            artifacts.c.content_type,
            artifacts.c.json,
            artifacts.c.bytes,
        ).where(artifacts.c.artifact_key == key)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).one_or_none()
        if row is None:
            raise ArtifactNotFound(key)
        content_type, json_val, bytes_val = row[0], row[1], row[2]
        if content_type == "application/json":
            if json_val is None:
                raise ArtifactNotFound(key)
            return json_val
        if content_type == "application/octet-stream":
            if bytes_val is None:
                raise ArtifactNotFound(key)
            return bytes_val
        if content_type == "application/x-parquet":
            if bytes_val is None:
                raise ArtifactNotFound(key)
            return parquet_bytes_to_df(bytes_val)
        raise TypeError(f"unknown content_type for artifact: {key} ({content_type})")

    def delete_run(self, run_id: str) -> int:
        if not run_id:
            raise ValueError("run_id must be non-empty")
        stmt = delete(artifacts).where(artifacts.c.artifact_key.like(f"{run_id}/%"))
        with self.engine.begin() as conn:
            res = conn.execute(stmt)
        return int(res.rowcount or 0)
