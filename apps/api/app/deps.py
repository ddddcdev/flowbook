"""
Dependency injection for the FastAPI app.

- FLOWBOOK_DATABASE_URL set → Postgres stores (production / field use)
- FLOWBOOK_DATABASE_URL unset → in-memory stores (development / smoke test)
"""

from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import text

from flowbook import Engine, Registry, discover_steps


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    registry = Registry()
    discover_steps(registry)

    database_url = os.environ.get("FLOWBOOK_DATABASE_URL")

    if database_url:
        from flowbook.extensions.postgres.artifacts_store import (
            PostgresArtifactsStore,
        )
        from flowbook.extensions.postgres.artifacts_store import (
            metadata as artifacts_meta,
        )
        from flowbook.extensions.postgres.config_store import (
            PostgresConfigStore,
        )
        from flowbook.extensions.postgres.config_store import (
            metadata as configs_meta,
        )

        store = PostgresArtifactsStore(database_url=database_url)
        config_store = PostgresConfigStore(database_url=database_url)

        # Drop + create artifacts schema (DB not in production yet; ensures latest schema)
        with store.engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS artifact_index CASCADE"))
        artifacts_meta.drop_all(store.engine)
        artifacts_meta.create_all(store.engine)
        configs_meta.create_all(config_store.engine)

        return Engine(
            store=store,
            registry=registry,
            config_store=config_store,
        )

    # Fallback: in-memory (no DATABASE_URL)
    from flowbook import InMemoryArtifactsStore, InMemoryConfigStore

    return Engine(
        store=InMemoryArtifactsStore(),
        registry=registry,
        config_store=InMemoryConfigStore(),
    )
