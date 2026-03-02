"""DB utilities: reset, seed from dir, seed defaults, seed artifact."""

from __future__ import annotations

import json
import os
import sys
import uuid
from importlib import resources
from pathlib import Path
from typing import Any


def get_bundled_configs_dir() -> Path | None:
    """Return path to bundled configs (flowbook/flowbook/configs/) or None if not found."""
    try:
        from flowbook.extensions import cli
        root = Path(cli.__file__).resolve().parent.parent.parent / "configs"
        return root if root.exists() else None
    except Exception:
        return None


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


def _seed_configs_from_dir_into_store(
    store: Any, root: Path, type_map: dict[str, Any]
) -> int:
    """Seed configs from a directory into an existing store. Returns count."""
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
    return total


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

    total = _seed_configs_from_dir_into_store(store, root, type_map)
    print(f"Done. Seeded {total} configs from {root}.")
    return 0


def seed_configs_from_bundled_and_overlay(overlay_dir: str | Path | None = None) -> int:
    """
    Seed from bundled configs (flowbook package), then overlay from overlay_dir if it exists.
    Use when flowbook[demo] is installed. Returns exit code.
    """
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

    bundled = get_bundled_configs_dir()
    if not bundled or not bundled.exists():
        print(
            "Bundled configs not found. Install flowbook[demo] or use --config-dir <path>.",
            file=sys.stderr,
        )
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

    total = _seed_configs_from_dir_into_store(store, bundled, type_map)
    print(f"Seeded {total} from bundled configs.", flush=True)

    overlay = Path(overlay_dir) if overlay_dir else None
    if overlay and overlay.exists():
        overlay_total = _seed_configs_from_dir_into_store(store, overlay, type_map)
        print(f"Overlaid {overlay_total} from {overlay}.", flush=True)
        total += overlay_total

    print(f"Done. Seeded {total} configs total.")
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
                "name": "import_excel",
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
                "name": "export_excel",
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
    key = "seed/demo/excel/result"
    store.put(key, {"smoke": True, "message": "seed for artifacts list"})
    print(f"Seeded artifact: {key}")
    return 0


def init_db_schema() -> int:
    """Create tables (entities, runs, results, artifacts, configs) for first-time setup.
    Use before flowbook db reset when the DB has no schema yet.
    Returns exit code."""
    if os.environ.get("FLOWBOOK_DB_RESET") != "1":
        print(
            "Refusing to run: set FLOWBOOK_DB_RESET=1 to confirm you want to modify the DB.",
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
            "Refusing to run: DSN does not look like localhost. Only local/dev DBs may be modified.",  # noqa: E501
            file=sys.stderr,
        )
        return 1

    database_url = _normalize_url(database_url)

    from sqlalchemy import create_engine, text

    engine = create_engine(database_url, future=True)
    schema_pkg = "flowbook.schema"
    files = ["10_artifacts.sql", "20_configs.sql"]

    with engine.begin() as conn:
        for name in files:
            sql = (resources.files(schema_pkg) / name).read_text(encoding="utf-8")
            conn.execute(text(sql))
            print(f"Executed {name}", flush=True)

    print("Schema created. You can now run flowbook db reset to seed configs.", flush=True)
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
        conn.execute(text("TRUNCATE artifacts, results, runs, entities CASCADE"))
        conn.execute(
            text(
                "INSERT INTO entities (entity_key, meta, created_at, updated_at) "
                "VALUES "
                "('demo', '{\"display_name\": \"Demo\", \"desc\": \"Top-level demo scope\"}'::jsonb, now(), now()), "
                "('demo/excel', '{\"display_name\": \"Demo Excel\", \"desc\": \"Excel import/export demo\"}'::jsonb, now(), now()) "
                "ON CONFLICT (entity_key) DO NOTHING"
            )
        )
    print("Cleared artifacts, results, runs, entities. Seeded demo, demo/excel.", flush=True)

    with config_store.engine.begin() as conn:
        conn.execute(text("TRUNCATE configs"))
    print("Cleared configs.", flush=True)

    bundled = get_bundled_configs_dir()
    if bundled and bundled.exists():
        overlay = None if str(config_dir).lower() == "bundled" else config_dir
        msg = "Seeding from bundled configs"
        if overlay:
            msg += f" + overlay {overlay}"
        print(msg + " ...", flush=True)
        return seed_configs_from_bundled_and_overlay(overlay)
    print("Seeding from config dir ...", flush=True)
    return seed_configs_from_dir(config_dir)
