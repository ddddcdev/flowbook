import os

import pandas as pd
from pandas.testing import assert_frame_equal

from flowbook.artifacts.postgres_store import PostgresArtifactsStore


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
