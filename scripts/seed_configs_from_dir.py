#!/usr/bin/env python3
"""Seed Postgres config store from JSON files under a directory.

Conventions:
- One JSON file per spec.
- Config name = file stem (e.g. configs/templates/import_excel.json -> name: "import_excel").

Directories:
- input_profiles -> InputProfile
- mappings -> Mapping
- templates -> PlanTemplate
- routing -> Routing

Usage:
  FLOWBOOK_DATABASE_URL=postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook \
    poetry run python scripts/seed_configs_from_dir.py --dir configs
"""

from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="configs", help="Config directory (default: configs)")
    args = parser.parse_args(argv)

    url = os.environ.get("FLOWBOOK_DATABASE_URL")
    if not url:
        print(
            "Set FLOWBOOK_DATABASE_URL (e.g. postgresql+psycopg://flowbook:flowbook@localhost:5432/flowbook)",
            file=sys.stderr,
        )
        print(
            "If the API uses Postgres, set the URL and run this script to seed configs. "
            "If the API runs without Postgres, configs/ are loaded from disk automatically.",
            file=sys.stderr,
        )
        return 1

    if url.startswith("postgresql://") and "+" not in url.split("//", 1)[0]:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]

    from sqlalchemy import text

    from flowbook.core.configs.spec_types import InputProfile, Mapping, PlanTemplate, Routing
    from flowbook.extensions.postgres.config_store import PostgresConfigStore
    from flowbook.extensions.postgres.config_store import metadata as configs_meta

    root = Path(args.dir)
    if not root.exists():
        raise FileNotFoundError(str(root))

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


if __name__ == "__main__":
    raise SystemExit(main())
