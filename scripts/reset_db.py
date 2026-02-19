#!/usr/bin/env python3
"""Full DB reset: truncate artifacts and configs, then seed configs from configs/.

**Safety**: Requires FLOWBOOK_DB_RESET=1 to run. Refuses prod-like DSNs.

Usage:
  FLOWBOOK_DATABASE_URL=... FLOWBOOK_DB_RESET=1 poetry run python scripts/reset_db.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if os.environ.get("FLOWBOOK_DB_RESET") != "1":
        print(
            "Refusing to run: set FLOWBOOK_DB_RESET=1 to confirm you want to wipe the DB.",
            file=sys.stderr,
        )
        return 1

    database_url = os.environ.get("FLOWBOOK_DATABASE_URL")
    if not database_url:
        print(
            "FLOWBOOK_DATABASE_URL is required. Set it in .env (see .env.example).",
            file=sys.stderr,
        )
        return 1

    # Refuse prod-like DSNs (simple heuristic: not localhost)
    if "localhost" not in database_url and "127.0.0.1" not in database_url:
        print(
            "Refusing to run: DSN does not look like localhost. Only local/dev DBs may be reset.",
            file=sys.stderr,
        )
        return 1

    if database_url.startswith("postgresql://") and "+" not in database_url.split("//", 1)[0]:
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://") :]

    from sqlalchemy import text

    from flowbook.extensions.postgres.artifacts_store import PostgresArtifactsStore
    from flowbook.extensions.postgres.config_store import PostgresConfigStore

    artifacts_store = PostgresArtifactsStore(database_url=database_url)
    config_store = PostgresConfigStore(database_url=database_url)

    with artifacts_store.engine.begin() as conn:
        conn.execute(text("TRUNCATE artifacts"))
    print("Cleared artifacts.", flush=True)

    with config_store.engine.begin() as conn:
        conn.execute(text("TRUNCATE configs"))
    print("Cleared configs.", flush=True)

    repo_root = Path(__file__).resolve().parent.parent
    seed_script = repo_root / "scripts" / "seed_configs_from_dir.py"
    print("Seeding from configs/ ...", flush=True)
    result = subprocess.run(
        [sys.executable, str(seed_script), "--dir", str(repo_root / "configs")],
        cwd=repo_root,
        env=os.environ,
    )
    if result.returncode != 0:
        return result.returncode

    print("Reset complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
