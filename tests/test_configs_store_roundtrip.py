# tests/test_postgres_config_store_roundtrip.py

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import text

from flowbook.configs.postgres_store import PostgresConfigStore


def _database_url() -> str:
    # 既存テストで使っている環境変数が不明なので多重フォールバック
    for k in ("FLOWBOOK_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL", "PG_URL"):
        v = os.getenv(k)
        if v:
            return v

    # infra/.env.postgres の典型値に寄せたデフォルト（必要なら調整）
    return "postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook"


@pytest.fixture
def config_store() -> PostgresConfigStore:
    return PostgresConfigStore(database_url=_database_url())


def _cleanup(store: PostgresConfigStore, kind: str, name: str) -> None:
    with store.engine.begin() as conn:
        conn.execute(
            text("DELETE FROM configs WHERE kind = :kind AND name = :name"),
            {"kind": kind, "name": name},
        )


def test_config_spec_roundtrip(config_store: PostgresConfigStore) -> None:
    kind = "mapping"
    name = f"test_roundtrip_{uuid4().hex}"
    config_id = str(uuid4())

    spec = {
        "ops": [
            {"op": "select_cols", "cols": ["a", "b"]},
            {"op": "rename", "map": {"a": "A"}},
        ]
    }

    try:
        config_store.put_spec(kind, name, spec, config_id=config_id)
        got = config_store.get_spec(kind, name)
        assert got == spec
    finally:
        _cleanup(config_store, kind, name)


def test_config_upsert_updates_spec(config_store: PostgresConfigStore) -> None:
    kind = "mapping"
    name = f"test_upsert_{uuid4().hex}"

    spec1 = {"ops": [{"op": "select_cols", "cols": ["a"]}]}
    spec2 = {"ops": [{"op": "select_cols", "cols": ["a", "b"]}]}

    try:
        config_store.put_spec(kind, name, spec1, config_id=str(uuid4()))
        assert config_store.get_spec(kind, name) == spec1

        # (kind, name) が同一なら upsert で更新される想定
        config_store.put_spec(kind, name, spec2, config_id=str(uuid4()))
        assert config_store.get_spec(kind, name) == spec2
    finally:
        _cleanup(config_store, kind, name)
