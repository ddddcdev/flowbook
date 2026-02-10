import os

import pandas as pd
import pytest

pytestmark = pytest.mark.integration
from pandas.testing import assert_frame_equal

from flowbook.artifacts.postgres_store import PostgresArtifactsStore
from flowbook.artifacts.scoped import RunScopedStore


def test_run_scoped_store_prevents_collisions():
    url = os.environ.get(
        "FLOWBOOK_DATABASE_URL",
        "postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook",
    )

    base = PostgresArtifactsStore(url)

    key = "artifact:data/same_key"
    df1 = pd.DataFrame({"x": [1, 2]})
    df2 = pd.DataFrame({"x": [9, 8]})

    s1 = RunScopedStore(base, "run-1")
    s2 = RunScopedStore(base, "run-2")

    s1.put_df(key, df1)
    s2.put_df(key, df2)

    assert_frame_equal(s1.get_df(key), df1, check_dtype=True)
    assert_frame_equal(s2.get_df(key), df2, check_dtype=True)
