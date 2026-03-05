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
    Column("meta", JSON, nullable=False, server_default="{}"),
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

results = Table(
    "results",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("entity_key", Text, primary_key=True),
    Column("result_artifacts_json", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("config_json", Text, nullable=True),
    Column("meta", JSON, nullable=False, server_default="{}"),
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


def _run_row_to_dict(row: Any) -> dict[str, Any]:
    """Convert runs Row to JSON-serializable dict."""
    return {
        "run_id": row.run_id,
        "status": row.status,
        "config_json": row.config_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _result_row_to_dict(row: Any) -> dict[str, Any]:
    """Convert results Row to JSON-serializable dict."""
    result_artifacts = None
    if getattr(row, "result_artifacts_json", None):
        try:
            result_artifacts = json.loads(row.result_artifacts_json)
        except (json.JSONDecodeError, TypeError):
            pass
    meta = {}
    if hasattr(row, "meta") and row.meta is not None:
        meta = dict(row.meta) if isinstance(row.meta, dict) else {}
    return {
        "run_id": row.run_id,
        "entity_key": row.entity_key,
        "result_artifacts": result_artifacts,
        "status": row.status,
        "config_json": row.config_json,
        "meta": meta,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


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
        self.upsert_entity(entity_key)
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

    def list_with_meta(self, prefix: str | None = None) -> list[dict[str, Any]]:
        """List artifacts with metadata (content_type, meta, created_at). Postgres only."""
        conditions = _list_where_from_prefix(prefix)
        stmt = select(
            artifacts.c.run_id,
            artifacts.c.entity_key,
            artifacts.c.artifact_path,
            artifacts.c.content_type,
            artifacts.c.meta,
            artifacts.c.created_at,
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(artifacts.c.run_id, artifacts.c.entity_key, artifacts.c.artifact_path)
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        result = []
        for r in rows:
            key = build_artifact_key(r[0], r[1], r[2])
            created_at = r[5]
            result.append(
                {
                    "key": key,
                    "content_type": r[3],
                    "meta": r[4] or {},
                    "created_at": created_at.isoformat() if created_at else None,
                }
            )
        return result

    def get_artifact_meta(self, key: str) -> dict[str, Any] | None:
        """Get artifact metadata without loading content. Returns None if not found."""
        run_id, entity_key, path = parse_artifact_key(key)
        stmt = select(
            artifacts.c.content_type,
            artifacts.c.meta,
            artifacts.c.created_at,
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
            return None
        return {
            "key": key,
            "content_type": row[0],
            "meta": row[1] or {},
            "created_at": row[2].isoformat() if row[2] else None,
        }

    # ---- Protocol: bytes ----
    def put_bytes(self, key: str, data: bytes, **kwargs: Any) -> str:
        run_id, entity_key, path = parse_artifact_key(key)
        self.upsert_entity(entity_key)
        meta_vals = self._meta_values(**kwargs)
        meta = dict(kwargs.get("meta") or {})
        vals = {
            "run_id": run_id,
            "entity_key": entity_key,
            "artifact_path": path,
            "content_type": "application/octet-stream",
            "codec": "none",
            "bytes": data,
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
        meta.update(kwargs.get("meta") or {})

        run_id, entity_key, path = parse_artifact_key(key)
        self.upsert_entity(entity_key)
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
        """Upsert runs row. Ensures run exists before results (FK)."""
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

    # ---- runs read API ----

    def list_runs(self, run_id: str | None = None) -> list[dict[str, Any]]:
        """List runs with optional run_id filter."""
        stmt = select(runs)
        if run_id is not None:
            stmt = stmt.where(runs.c.run_id == run_id)
        stmt = stmt.order_by(runs.c.updated_at.desc())
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        return [_run_row_to_dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get single run by run_id. Returns None if not found."""
        stmt = select(runs).where(runs.c.run_id == run_id)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).one_or_none()
        if row is None:
            return None
        return _run_row_to_dict(row)

    def upsert_entity(self, entity_key: str) -> None:
        """Upsert entities row. Ensures entity exists when first used. ON CONFLICT DO NOTHING.
        Skips entity_keys with ':' (e.g. artifact:input) - those are logical addresses, not scopes.
        """
        if not entity_key or ":" in entity_key:
            return
        stmt = (
            pg_insert(entities)
            .values(entity_key=entity_key)
            .on_conflict_do_nothing(index_elements=["entity_key"])
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def list_entities(self) -> list[dict[str, Any]]:
        """List all entities. Returns list of {entity_key, meta, created_at, updated_at}."""
        stmt = select(entities).order_by(entities.c.entity_key)
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()
        return [
            {
                "entity_key": r.entity_key,
                "meta": r.meta or {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]

    def upsert_result(
        self,
        run_id: str,
        entity_key: str,
        status: str,
        run_config_json: str | None = None,
        entity_config_json: str | None = None,
        result_artifacts: list[dict[str, str | None]] | None = None,
        meta: dict | None = None,
    ) -> None:
        """Upsert results row for (run_id, entity_key). Ensures runs and entities exist first.
        result_artifacts: list of {path, label} for main results. When plan has no result_artifacts,
        executor derives from last step's output.
        meta: optional JSONB for target_month, effective_date, etc.
        """
        self.upsert_run(run_id, status, config_json=run_config_json)
        self.upsert_entity(entity_key)
        result_artifacts_json = json.dumps(result_artifacts) if result_artifacts else None
        meta_dict = meta if meta is not None else {}
        vals = {
            "run_id": run_id,
            "entity_key": entity_key,
            "status": status,
            "result_artifacts_json": result_artifacts_json,
            "config_json": entity_config_json,
            "meta": meta_dict,
        }
        set_cols: dict[str, object] = {
            "status": status,
            "updated_at": text("now()"),
        }
        if result_artifacts_json is not None:
            set_cols["result_artifacts_json"] = result_artifacts_json
        if entity_config_json is not None:
            set_cols["config_json"] = entity_config_json
        if meta is not None:
            set_cols["meta"] = meta_dict
        stmt = (
            pg_insert(results)
            .values(**vals)
            .on_conflict_do_update(
                index_elements=["run_id", "entity_key"],
                set_=set_cols,
            )
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    # ---- results read API ----

    def list_results(
        self,
        run_id: str | None = None,
        entity_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """List results with optional run_id and entity_key filters.

        - run_id: results within a run.
        - entity_key: history of runs for that entity across runs.
        """
        stmt = select(results)
        conditions = []
        if run_id is not None:
            conditions.append(results.c.run_id == run_id)
        if entity_key is not None:
            conditions.append(results.c.entity_key == entity_key)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(results.c.updated_at.desc())

        with self.engine.begin() as conn:
            rows = conn.execute(stmt).all()

        return [_result_row_to_dict(row) for row in rows]

    def get_result(self, run_id: str, entity_key: str) -> dict[str, Any] | None:
        """Get single result by (run_id, entity_key). Returns None if not found."""
        stmt = select(results).where(
            and_(
                results.c.run_id == run_id,
                results.c.entity_key == entity_key,
            )
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt).one_or_none()
        if row is None:
            return None
        return _result_row_to_dict(row)

    def list_latest_results(
        self,
        entity_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """List latest result per entity_key (updated_at max). No new table."""
        cols_str = (
            "run_id, entity_key, result_artifacts_json, status, config_json, meta, "
            "created_at, updated_at"
        )
        raw_sql = (
            f"SELECT {cols_str} FROM ("
            f"SELECT DISTINCT ON (entity_key) {cols_str} "
            "FROM results"
            + (" WHERE entity_key = :entity_key" if entity_key else "")
            + " ORDER BY entity_key, updated_at DESC"
            ") sub"
        )
        with self.engine.begin() as conn:
            if entity_key:
                rows = conn.execute(text(raw_sql), {"entity_key": entity_key}).all()
            else:
                rows = conn.execute(text(raw_sql)).all()

        cols = [
            "run_id",
            "entity_key",
            "result_artifacts_json",
            "status",
            "config_json",
            "meta",
            "created_at",
            "updated_at",
        ]
        result = []
        for row in rows:
            d = dict(zip(cols, row, strict=True))
            result_artifacts = None
            if d.get("result_artifacts_json"):
                try:
                    result_artifacts = json.loads(d["result_artifacts_json"])
                except (json.JSONDecodeError, TypeError):
                    pass
            d["result_artifacts"] = result_artifacts
            del d["result_artifacts_json"]
            meta_val = d.get("meta")
            d["meta"] = dict(meta_val) if isinstance(meta_val, dict) else {}
            for k in ("created_at", "updated_at"):
                v = d.get(k)
                if v is not None and hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            result.append(d)
        return result

    def get_latest_result(self, entity_key: str) -> dict[str, Any] | None:
        """Get latest result for entity_key (updated_at max). Returns None if not found."""
        rows = self.list_latest_results(entity_key=entity_key)
        return rows[0] if rows else None
