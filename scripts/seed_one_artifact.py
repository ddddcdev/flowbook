#!/usr/bin/env python3
"""
Seed one artifact into the Postgres store so that `flowbook-dev artifacts list`
shows at least one row.

Usage:
  FLOWBOOK_DATABASE_URL=postgresql://flowbook:flowbook@localhost:5432/flowbook \
    poetry run python scripts/seed_one_artifact.py

Then start the API with the same FLOWBOOK_DATABASE_URL and run:
  poetry run flowbook-dev artifacts list
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    url = os.environ.get("FLOWBOOK_DATABASE_URL")
    if not url:
        print(
            "Set FLOWBOOK_DATABASE_URL (e.g. postgresql://flowbook:flowbook@localhost:5432/flowbook)",
            file=sys.stderr,
        )
        return 1

    from flowbook.extensions.postgres.artifacts_store import (
        PostgresArtifactsStore,
        metadata,
    )

    store = PostgresArtifactsStore(database_url=url)
    metadata.create_all(store.engine)
    key = "smoke-test/artifact"
    store.put(key, {"smoke": True, "message": "seed for artifacts list"})
    print(f"Seeded artifact: {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
