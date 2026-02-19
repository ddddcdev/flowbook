#!/usr/bin/env python3
"""
Seed config store with InputProfile and PlanTemplates so the API can run
inspect, import, and export.

Use once before manual verification when using Postgres:

  FLOWBOOK_DATABASE_URL=postgresql://flowbook:flowbook@localhost:5432/flowbook \
    poetry run python scripts/seed_config_for_api.py

Then start the API with the same FLOWBOOK_DATABASE_URL.
"""

from __future__ import annotations

import os
import sys
import uuid


def main() -> int:
    url = os.environ.get("FLOWBOOK_DATABASE_URL")
    if not url:
        print(
            "Set FLOWBOOK_DATABASE_URL (e.g. postgresql://flowbook:flowbook@localhost:5432/flowbook)",
            file=sys.stderr,
        )
        return 1

    from flowbook.core.configs.spec_types import InputProfile, PlanTemplate
    from flowbook.extensions.postgres.config_store import (
        PostgresConfigStore,
    )
    from flowbook.extensions.postgres.config_store import (
        metadata as configs_meta,
    )

    store = PostgresConfigStore(database_url=url)
    configs_meta.create_all(store.engine)

    # InputProfile for inspect (kind_rules + date_rule for real_input.xlsx)
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

    # PlanTemplate for import: read_excel_bytes → df artifact
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

    # PlanTemplate for export: write DataFrame to Excel bytes
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


if __name__ == "__main__":
    sys.exit(main())
