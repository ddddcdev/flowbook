"""DB utilities: reset, seed from dir, seed defaults, seed artifact."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return obj


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://") and "+" not in url.split("//", 1)[0]:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def seed_configs_from_dir(config_dir: str | Path) -> int:
    """Seed Postgres config store from JSON files under a directory. Returns exit code."""
    url = os.environ.get("FLOWBOOK_DATABASE_URL")
    if not url:
        print(
            "Set FLOWBOOK_DATABASE_URL (e.g. postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook)",
            file=sys.stderr,
        )
        return 1

    url = _normalize_url(url)

    from sqlalchemy import text

    from flowbook.core.configs.spec_types import InputProfile, Mapping, PlanTemplate, Routing
    from flowbook.extensions.postgres.config_store import PostgresConfigStore
    from flowbook.extensions.postgres.config_store import metadata as configs_meta

    root = Path(config_dir)
    if not root.exists():
        print(f"Config directory not found: {root}", file=sys.stderr)
        return 1

    store = PostgresConfigStore(database_url=url)
    configs_meta.create_all(store.engine)
    with store.engine.begin() as conn:
        conn.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS configs_kind_name_uq ON configs(kind, name)")
        )

    type_map: dict[str, Any] = {
        "input_profiles": InputProfile,
        "mappings": Mapping,
        "templates": PlanTemplate,
        "routing": Routing,
    }

    total = 0
    for subdir, spec_type in type_map.items():
        d = root / subdir
        if not d.exists():
            continue

        for p in sorted(d.glob("*.json")):
            name = p.stem
            spec = _load_json(p)
            store.put_spec(spec_type, name, spec, config_id=str(uuid.uuid4()))
            print(f"Seeded {spec_type.__name__}: {name}")
            total += 1

    print(f"Done. Seeded {total} configs from {root}.")
    return 0


def seed_config_for_api() -> int:
    """Seed hardcoded InputProfile and PlanTemplates for API smoke test. Returns exit code."""
    url = os.environ.get("FLOWBOOK_DATABASE_URL")
    if not url:
        print(
            "Set FLOWBOOK_DATABASE_URL (e.g. postgresql://flowbook:flowbook@localhost:5432/flowbook)",
            file=sys.stderr,
        )
        return 1

    url = _normalize_url(url)

    from flowbook.core.configs.spec_types import InputProfile, PlanTemplate
    from flowbook.extensions.postgres.config_store import PostgresConfigStore
    from flowbook.extensions.postgres.config_store import metadata as configs_meta

    store = PostgresConfigStore(database_url=url)
    configs_meta.create_all(store.engine)

    store.put_spec(
        InputProfile,
        "source",
        {
            "kind_rules": [
                {"pattern": r"^fileA_.*\.xlsx$", "kind": "fileA"},
                {"pattern": r"^real_input\.xlsx$", "kind": "fileA"},
            ],
            "date_rule": {"sheet": "meta", "cell": "B2"},
        },
        config_id=str(uuid.uuid4()),
    )
    print("Seeded InputProfile: source")

    store.put_spec(
        PlanTemplate,
        "import_excel",
        {
            "plan": {
                "steps": [
                    {
                        "name": "read",
                        "op": "read_excel_bytes",
                        "inputs": {
                            "src_excel_bytes": "@src_excel_bytes",
                            "sheet": "@sheet_name",
                            "header": "@header_row",
                        },
                    }
                ]
            }
        },
        config_id=str(uuid.uuid4()),
    )
    print("Seeded PlanTemplate: import_excel")

    store.put_spec(
        PlanTemplate,
        "export_excel",
        {
            "plan": {
                "steps": [
                    {
                        "name": "write",
                        "op": "write_excel",
                        "inputs": {"df": "@in_key"},
                    }
                ]
            }
        },
        config_id=str(uuid.uuid4()),
    )
    print("Seeded PlanTemplate: export_excel")

    print("Done. Start the API and use /inspect, /import, /export.")
    return 0


def seed_one_artifact() -> int:
    """Seed one smoke-test artifact for flowbook artifacts list. Returns exit code."""
    url = os.environ.get("FLOWBOOK_DATABASE_URL")
    if not url:
        print(
            "Set FLOWBOOK_DATABASE_URL (e.g. postgresql://flowbook:flowbook@localhost:5432/flowbook)",
            file=sys.stderr,
        )
        return 1

    url = _normalize_url(url)

    from flowbook.extensions.postgres.artifacts_store import PostgresArtifactsStore, metadata

    store = PostgresArtifactsStore(database_url=url)
    metadata.create_all(store.engine)
    key = "smoke-test/artifact"
    store.put(key, {"smoke": True, "message": "seed for artifacts list"})
    print(f"Seeded artifact: {key}")
    return 0


def reset_db(config_dir: str | Path) -> int:
    """Truncate artifacts and configs, then seed from config dir. Returns exit code."""
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

    if "localhost" not in database_url and "127.0.0.1" not in database_url:
        print(
            "Refusing to run: DSN does not look like localhost. Only local/dev DBs may be reset.",
            file=sys.stderr,
        )
        return 1

    database_url = _normalize_url(database_url)

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

    print("Seeding from config dir ...", flush=True)
    return seed_configs_from_dir(config_dir)
