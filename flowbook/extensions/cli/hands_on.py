"""Interactive hands-on flow: Health -> Inspect -> Import -> Artifacts -> Export -> Download."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx


def run(
    base_url: str = "http://127.0.0.1:8000",
    fixture_path: str | Path = "tests/fixtures/excel/test_detect_region_input.xlsx",
    config_dir: str | Path = "configs",
    interactive: bool = True,
) -> int:
    """Run the hands-on flow. Returns exit code."""
    fixture = Path(fixture_path)
    if not fixture.exists():
        print(f"Fixture not found: {fixture}", file=sys.stderr)
        print(
            "Generate with: flowbook fixture generate -o tests/fixtures/excel/",
            file=sys.stderr,
        )
        return 1

    base = base_url.rstrip("/")

    def _prompt(msg: str = "Press Enter to continue...") -> None:
        if interactive:
            input(msg)

    # Optional: full init
    if interactive:
        init_ans = input("Full init DB (clear artifacts + configs, then seed)? [Y/n] ").strip()
        if init_ans.lower() != "n":
            from flowbook.extensions.cli.db import reset_db

            if os.environ.get("FLOWBOOK_DB_RESET") != "1":
                os.environ["FLOWBOOK_DB_RESET"] = "1"
            code = reset_db(config_dir)
            if code != 0:
                return code
            _prompt()
        else:
            print("Skipping init.")

    # Step 1: Health
    print("\n=== Step 1: Health ===")
    try:
        r = httpx.get(f"{base}/health", timeout=10.0)
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
    except httpx.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    _prompt()

    # Step 2: Inspect
    print("\n=== Step 2: Inspect ===")
    try:
        with open(fixture, "rb") as f:
            r = httpx.post(
                f"{base}/inspect",
                files={
                    "file": (
                        fixture.name,
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                data={"input_profile_name": "source"},
                timeout=30.0,
            )
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
    except httpx.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    _prompt()

    # Step 3: Import
    print("\n=== Step 3: Import (table extract) ===")
    try:
        with open(fixture, "rb") as f:
            r = httpx.post(
                f"{base}/import",
                files={
                    "file": (
                        fixture.name,
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                data={
                    "template_name": "import_excel_region",
                    "sheet_name": "data",
                    "region_profile_name": "detail_region",
                },
                timeout=60.0,
            )
        r.raise_for_status()
        import_data = r.json()
        print(json.dumps(import_data, indent=2))
    except httpx.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    run_id = import_data.get("run_id", "")
    read_df_key = ""
    for k in import_data.get("artifacts_written", []):
        if k.endswith("/read/df"):
            read_df_key = k
            break
    print(f"\nrun_id: {run_id}")
    print(f"read/df key (imported): {read_df_key}")
    _prompt()

    # Step 4: List artifacts
    print("\n=== Step 4: List artifacts ===")
    try:
        r = httpx.get(f"{base}/artifacts", timeout=30.0)
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
    except httpx.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    _prompt()

    # Step 5: Export
    bytes_key = ""
    print("\n=== Step 5: Export (filter/map from import) ===")
    if not read_df_key:
        print("No read/df key from Step 3. Export skipped.")
    else:
        try:
            r = httpx.post(
                f"{base}/export/from_artifact",
                data={"source_artifact_key": read_df_key, "mapping_name": "detect_region_test"},
                timeout=60.0,
            )
            r.raise_for_status()
            export_data = r.json()
            for k in export_data.get("artifacts_written", []):
                if k.endswith("/write/bytes"):
                    bytes_key = k
                    break
            print(json.dumps(export_data, indent=2))
            print(f"\nwrite/bytes key (exported): {bytes_key}")
        except httpx.HTTPError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    _prompt()

    # Step 6: Download
    print("\n=== Step 6: Download ===")
    imported_file = Path("demo_imported.xlsx")
    exported_file = Path("demo_exported.xlsx")
    if read_df_key:
        try:
            r = httpx.get(f"{base}/artifacts/{read_df_key}/as_excel", timeout=60.0)
            r.raise_for_status()
            imported_file.write_bytes(r.content)
            print(f"Saved imported: {imported_file}")
        except httpx.HTTPError as e:
            print(f"Download error: {e}", file=sys.stderr)
    if bytes_key:
        try:
            r = httpx.get(f"{base}/artifacts/{bytes_key}/raw", timeout=60.0)
            r.raise_for_status()
            exported_file.write_bytes(r.content)
            print(f"Saved exported: {exported_file}")
        except httpx.HTTPError as e:
            print(f"Download error: {e}", file=sys.stderr)
    if not read_df_key and not bytes_key:
        print("Could not determine keys. Download manually.")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
