from __future__ import annotations

import os
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy import text

from flowbook import DefaultRunStore
from flowbook.core.configs.spec_types import Mapping
from flowbook.extensions.postgres import PostgresArtifactsStore, PostgresConfigStore
from flowbook.extensions.steps.apply_mapping import ApplyMappingOp, apply_mapping_op

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
        for k in keys:
            parts = k.split("/", 2)
            if len(parts) == 3:
                conn.execute(
                    text(
                        "DELETE FROM artifacts "
                        "WHERE run_id = :r AND entity_key = :e AND artifact_path = :p"
                    ),
                    {"r": parts[0], "e": parts[1], "p": parts[2]},
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

    mapping_name = f"m_{uuid4().hex}"
    config_id = str(uuid4())

    spec = {
        "ops": [
            {"op": "select_cols", "cols": ["a", "b"]},
            {"op": "rename", "map": {"a": "A"}},
            {"op": "filter_rows", "expr": "A > 0"},
        ]
    }

    df = pd.DataFrame({"a": [1, -1, 2], "b": [10, 20, 30], "x": [9, 9, 9]})

    try:
        configs.put_spec(Mapping, mapping_name, spec, config_id=config_id)

        result = apply_mapping_op(
            {
                ApplyMappingOp.Inputs.DF: df,
                ApplyMappingOp.Inputs.MAPPING_NAME: mapping_name,
            },
            store,
        )

        out = result[ApplyMappingOp.Outputs.DF]
        assert list(out.columns) == ["A", "b"]
        assert out["A"].tolist() == [1, 2]
        assert out["b"].tolist() == [10, 30]
    finally:
        _cleanup_config(configs, Mapping.KIND, mapping_name)
