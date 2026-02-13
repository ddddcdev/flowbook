import os

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from sqlalchemy import create_engine, text

from flowbook.extensions.postgres import PostgresArtifactsStore

pytestmark = pytest.mark.integration


def test_df_roundtrip_across_store_instances():
    url = os.environ.get(
        "FLOWBOOK_DATABASE_URL",
        "postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook",
    )

    key = "artifact:data/df_roundtrip"

    df0 = pd.DataFrame(
        {"a": [1, 2, 3], "b": ["x", "y", "z"]},
        index=pd.Index([10, 20, 30], name="idx"),
    )

    store1 = PostgresArtifactsStore(url)
    store1.put_df(key, df0)

    store2 = PostgresArtifactsStore(url)
    df1 = store2.get_df(key)

    assert_frame_equal(df0, df1, check_dtype=True)


def test_df_meta_stored():
    """Test that metadata (row_count, col_count, columns, schema) is stored in artifacts.meta."""
    url = os.environ.get(
        "FLOWBOOK_DATABASE_URL",
        "postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook",
    )

    key = "artifact:data/df_meta_test"

    df = pd.DataFrame(
        {"name": ["Alice", "Bob"], "age": [25, 30], "score": [95.5, 87.3]},
    )

    store = PostgresArtifactsStore(url)
    store.put_df(key, df)

    # Verify all meta fields via raw SQL
    engine = create_engine(url, future=True)
    stmt = text("""
        SELECT 
            meta->>'row_count' as row_count,
            meta->>'col_count' as col_count,
            meta->'columns' as columns,
            meta->'schema' as schema
        FROM artifacts 
        WHERE artifact_key = :key
    """)
    with engine.begin() as conn:
        result = conn.execute(stmt, {"key": key}).one()

    row_count, col_count, columns, schema = result
    assert row_count == "2"
    assert col_count == "3"
    assert columns == ["name", "age", "score"]
    assert "name" in schema and "age" in schema and "score" in schema
