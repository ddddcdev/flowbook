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
    and_,
    create_engine,
    delete,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import insert as pg_insert

from flowbook.core.artifacts.key_utils import build_artifact_key, parse_artifact_key
from flowbook.core.artifacts.store import ArtifactNotFound, ArtifactsStore, JsonValue

metadata = MetaData()


entities = Table(
    "entities",
    metadata,
    Column("entity_key", Text, primary_key=True),
    Column("meta_json", Text, nullable=True),
)

runs = Table(
    "runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("status", Text, nullable=False),
    Column("config_json", Text, nullable=True),
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

entity_runs = Table(
    "entity_runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("entity_key", Text, primary_key=True),
    Column("artifact_path", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("config_json", Text, nullable=True),
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

artifacts = Table(
    "artifacts",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("entity_key", Text, primary_key=True),
    Column("artifact_path", Text, primary_key=True),
    Column("content_type", Text, nullable=False),
    Column("codec", Text, nullable=False, server_default="none"),
    Column("bytes", LargeBinary, nullable=True),
    Column("json", JSON, nullable=True),
    Column("meta", JSON, nullable=False, server_default="{}"),
    Column("created_at", TIMESTAMP(timezone=True), nullable=True),
)


def df_to_parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, engine="pyarrow", index=True)
    return buf.getvalue()


def parquet_bytes_to_df(b: bytes) -> pd.DataFrame:
    buf = io.BytesIO(b)
    return pd.read_parquet(buf, engine="pyarrow")


def _list_where_from_prefix(prefix: str | None) -> list:
    """Build WHERE clause from prefix. Returns list of conditions.
    Prefix matches keys where run_id/entity_key/path starts with prefix.
    """
    if prefix is None or prefix == "":
        return []
    prefix_pattern = prefix.rstrip("/") + "%"
    key_expr = artifacts.c.run_id + "/" + artifacts.c.entity_key + "/" + artifacts.c.artifact_path
    return [key_expr.like(prefix_pattern)]


@dataclass
class PostgresArtifactsStore(ArtifactsStore):
    database_url: str

    def __post_init__(self) -> None:
        self.engine = create_engine(self.database_url, future=True)

    def _meta_values(self, **kwargs: Any) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if "created_at" in kwargs:
            out["created_at"] = kwargs["created_at"]
        return out

    # ---- Protocol: JSON only ----
    def put(self, key: str, value: JsonValue, **kwargs: Any) -> str:
        try:
            json.dumps(value)
        except TypeError as e:
            raise TypeError(f"put expects JSON-serializable value: key={key}") from e

        run_id, entity_key, path = parse_artifact_key(key)
        meta_vals = self._meta_values(**kwargs)
        vals = {
            "run_id": run_id,
            "entity_key": entity_key,
            "artifact_path": path,
            "content_type": "application/json",
            "codec": "none",
            "bytes": None,
            "json": value,
            "meta": {},
            **meta_vals,
        }
        pk_cols = ("run_id", "entity_key", "artifact_path")
        set_cols = {k: v for k, v in vals.items() if k not in pk_cols}

        stmt = (
            pg_insert(artifacts)
            .values(**vals)
            .on_conflict_do_update(
                index_elements=["run_id", "entity_key", "artifact_path"],
                set_=set_cols,
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        return key

    def get(self, key: str) -> JsonValue:
        run_id, entity_key, path = parse_artifact_key(key)
        stmt = select(artifacts.c.json).where(
            and_(
                artifacts.c.run_id == run_id,
                artifacts.c.entity_key == entity_key,
                artifacts.c.artifact_path == path,
            )
        )
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
        conditions = _list_where_from_prefix(prefix)
        stmt = select(artifacts.c.run_id, artifacts.c.entity_key, artifacts.c.artifact_path)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(artifacts.c.run_id, artifacts.c.entity_key, artifacts.c.artifact_path)

        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        return [build_artifact_key(r[0], r[1], r[2]) for r in rows]

    # ---- Protocol: bytes ----
    def put_bytes(self, key: str, data: bytes, **kwargs: Any) -> str:
        run_id, entity_key, path = parse_artifact_key(key)
        meta_vals = self._meta_values(**kwargs)
        vals = {
            "run_id": run_id,
            "entity_key": entity_key,
            "artifact_path": path,
            "content_type": "application/octet-stream",
            "codec": "none",
            "bytes": data,
            "json": None,
            "meta": {},
            **meta_vals,
        }
        pk_cols = ("run_id", "entity_key", "artifact_path")
        set_cols = {k: v for k, v in vals.items() if k not in pk_cols}
        stmt = (
            pg_insert(artifacts)
            .values(**vals)
            .on_conflict_do_update(
                index_elements=["run_id", "entity_key", "artifact_path"],
                set_=set_cols,
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        return key

    def get_bytes(self, key: str) -> bytes:
        run_id, entity_key, path = parse_artifact_key(key)
        stmt = select(artifacts.c.bytes).where(
            and_(
                artifacts.c.run_id == run_id,
                artifacts.c.entity_key == entity_key,
                artifacts.c.artifact_path == path,
            )
        )
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

        run_id, entity_key, path = parse_artifact_key(key)
        meta_vals = self._meta_values(**kwargs)
        vals = {
            "run_id": run_id,
            "entity_key": entity_key,
            "artifact_path": path,
            "content_type": "application/x-parquet",
            "codec": "parquet",
            "bytes": b,
            "json": None,
            "meta": meta,
            **meta_vals,
        }
        pk_cols = ("run_id", "entity_key", "artifact_path")
        set_cols = {k: v for k, v in vals.items() if k not in pk_cols}
        stmt = (
            pg_insert(artifacts)
            .values(**vals)
            .on_conflict_do_update(
                index_elements=["run_id", "entity_key", "artifact_path"],
                set_=set_cols,
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
        return key

    def get_df(self, key: str) -> pd.DataFrame:
        return parquet_bytes_to_df(self.get_bytes(key))

    def get_any(self, key: str) -> JsonValue | bytes | pd.DataFrame:
        run_id, entity_key, path = parse_artifact_key(key)
        stmt = select(
            artifacts.c.content_type,
            artifacts.c.json,
            artifacts.c.bytes,
        ).where(
            and_(
                artifacts.c.run_id == run_id,
                artifacts.c.entity_key == entity_key,
                artifacts.c.artifact_path == path,
            )
        )
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
        stmt = delete(artifacts).where(artifacts.c.run_id == run_id)
        with self.engine.begin() as conn:
            res = conn.execute(stmt)
        return int(res.rowcount or 0)

    def upsert_run(
        self,
        run_id: str,
        status: str,
        config_json: str | None = None,
    ) -> None:
        """Upsert runs row. Ensures run exists before entity_runs (FK)."""
        set_cols: dict[str, object] = {"status": status, "updated_at": text("now()")}
        if config_json is not None:
            set_cols["config_json"] = config_json
        stmt = (
            pg_insert(runs)
            .values(run_id=run_id, status=status, config_json=config_json)
            .on_conflict_do_update(
                index_elements=["run_id"],
                set_=set_cols,
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def upsert_entity(self, entity_key: str) -> None:
        """Upsert entities row. Ensures entity exists when first used."""
        stmt = (
            pg_insert(entities)
            .values(entity_key=entity_key)
            .on_conflict_do_nothing(index_elements=["entity_key"])
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def upsert_entity_run(
        self,
        run_id: str,
        entity_key: str,
        status: str,
        artifact_path: str | None = None,
        run_config_json: str | None = None,
        entity_config_json: str | None = None,
    ) -> None:
        """Upsert entity_runs row for (run_id, entity_key). Ensures runs and entities exist first.
        artifact_path: Primary step output path (e.g. inspect/result, read/df).
        """
        self.upsert_run(run_id, status, config_json=run_config_json)
        self.upsert_entity(entity_key)
        vals = {
            "run_id": run_id,
            "entity_key": entity_key,
            "status": status,
            "artifact_path": artifact_path,
            "config_json": entity_config_json,
        }
        set_cols: dict[str, object] = {
            "status": status,
            "updated_at": text("now()"),
        }
        if artifact_path is not None:
            set_cols["artifact_path"] = artifact_path
        if entity_config_json is not None:
            set_cols["config_json"] = entity_config_json
        stmt = (
            pg_insert(entity_runs)
            .values(**vals)
            .on_conflict_do_update(
                index_elements=["run_id", "entity_key"],
                set_=set_cols,
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
