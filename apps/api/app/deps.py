"""
Dependency injection for the FastAPI app.

- FLOWBOOK_DATABASE_URL set → Postgres stores (production / field use)
- FLOWBOOK_DATABASE_URL unset → in-memory stores (development / smoke test)
"""

from __future__ import annotations

import os
from functools import lru_cache

from flowbook import Engine, Registry, register_steps


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    registry = Registry()
    register_steps(registry)

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

        # Ensure tables exist (idempotent)
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
