import os

import pytest

from flowbook.extensions.postgres import PostgresArtifactsStore

pytestmark = pytest.mark.integration


def test_delete_run_removes_prefixed_keys():
    url = os.environ.get(
        "FLOWBOOK_DATABASE_URL",
        "postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook",
    )
    store = PostgresArtifactsStore(url)

    run_id = "run_test_delete"
    store.put(f"{run_id}/artifact:input/x", 1)
    store.put(f"{run_id}/artifact:input/y", 2)
    store.put("other_run/artifact:input/x", 9)

    deleted = store.delete_run(run_id)
    assert deleted >= 2

    keys = store.list(prefix=f"{run_id}/")
    assert keys == []
