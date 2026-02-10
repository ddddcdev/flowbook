from __future__ import annotations

import os
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy import text

from extensions.steps.apply_mapping import apply_mapping_op
from flowbook.artifacts.postgres_store import PostgresArtifactsStore
from flowbook.configs.postgres_store import PostgresConfigStore
from flowbook.runtime.default_store import DefaultRunStore

pytestmark = pytest.mark.integration


def _database_url() -> str:
    for k in ("FLOWBOOK_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL", "PG_URL"):
        v = os.getenv(k)
        if v:
            return v
    return "postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook"


def _cleanup(store: PostgresArtifactsStore, keys: list[str]) -> None:
    if not keys:
        return
    with store.engine.begin() as conn:
        conn.execute(
            text("DELETE FROM artifacts WHERE artifact_key = ANY(:keys)"),
            {"keys": keys},
        )


def _cleanup_config(cfg: PostgresConfigStore, kind: str, name: str) -> None:
    with cfg.engine.begin() as conn:
        conn.execute(
            text("DELETE FROM configs WHERE kind = :kind AND name = :name"),
            {"kind": kind, "name": name},
        )


def test_apply_mapping_op_df_to_df() -> None:
    db = _database_url()

    artifacts = PostgresArtifactsStore(database_url=db)
    configs = PostgresConfigStore(database_url=db)

    store = DefaultRunStore(artifacts=artifacts, configs=configs)

    kind = "mapping"
    mapping_name = f"m_{uuid4().hex}"
    config_id = str(uuid4())

    spec = {
        "ops": [
            {"op": "select_cols", "cols": ["a", "b"]},
            {"op": "rename", "map": {"a": "A"}},
            {"op": "filter_rows", "expr": "A > 0"},
        ]
    }

    in_key = f"test/{uuid4().hex}/in"
    out_key = f"test/{uuid4().hex}/out"

    df = pd.DataFrame({"a": [1, -1, 2], "b": [10, 20, 30], "x": [9, 9, 9]})

    try:
        configs.put_spec(kind, mapping_name, spec, config_id=config_id)
        artifacts.put_df(in_key, df)

        apply_mapping_op(
            {"in_key": in_key, "out_key": out_key, "mapping_name": mapping_name},
            store,
        )

        out = artifacts.get_df(out_key)
        assert list(out.columns) == ["A", "b"]
        assert out["A"].tolist() == [1, 2]
        assert out["b"].tolist() == [10, 30]
    finally:
        _cleanup(artifacts, [in_key, out_key])
        _cleanup_config(configs, kind, mapping_name)
