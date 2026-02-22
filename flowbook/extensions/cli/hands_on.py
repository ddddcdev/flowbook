"""Interactive hands-on: Health -> Inspect -> Import -> Verify -> Export -> Verify -> Download."""

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
                data={"entity_key": "demo/excel", "input_profile_name": "source"},
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
                    "entity_key": "demo/excel",
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
    entity_key = "demo/excel"
    read_df_key = ""
    for k in import_data.get("artifacts_written", []):
        if k.endswith("/read/df"):
            read_df_key = k
            break
    print(f"\nrun_id: {run_id}")
    print(f"read/df key (from import): {read_df_key}")
    _prompt()

    # Step 4: Verify runs, entity_runs, artifacts (created by import)
    print("\n=== Step 4: Verify runs, entity_runs, artifacts ===")
    print("Confirm what Import created; keys here will be used for Export and Download.")
    try:
        # runs (Postgres only; InMemory returns empty)
        r_runs = httpx.get(f"{base}/runs", params={"run_id": run_id}, timeout=10.0)
        if r_runs.status_code == 200 and r_runs.json().get("entries"):
            print("runs (this run):")
            for rn in r_runs.json()["entries"]:
                print(f"  - {rn['run_id']} status={rn['status']}")
        else:
            print("runs: (empty or not available)")
        # entity_runs for this run (Postgres only; InMemory returns empty)
        r_er = httpx.get(f"{base}/entity_runs", params={"run_id": run_id}, timeout=10.0)
        if r_er.status_code == 200 and r_er.json().get("entries"):
            print("entity_runs (this run):")
            for ent in r_er.json()["entries"]:
                ap = ent.get("artifact_path") or ""
                ri, ek, st = ent["run_id"], ent["entity_key"], ent["status"]
                print(f"  - {ri}/{ek} status={st} artifact_path={ap}")
            # Get details to confirm artifact_path
            r_er_get = httpx.get(f"{base}/entity_runs/{run_id}/{entity_key}", timeout=10.0)
            if r_er_get.status_code == 200:
                detail = r_er_get.json()
                ap = detail.get("artifact_path")
                if ap:
                    read_df_key = f"{run_id}/{entity_key}/{ap}"
                    print(f"  -> read_df_key from entity_run: {read_df_key}")
        else:
            print("entity_runs: (empty or not available; using import response)")
        # Artifacts for this run
        r_art = httpx.get(f"{base}/artifacts", params={"prefix": f"{run_id}/"}, timeout=10.0)
        r_art.raise_for_status()
        art_data = r_art.json()
        keys = art_data.get("keys", [])
        print(f"\nartifacts (prefix={run_id}/): {len(keys)} keys")
        for k in keys[:10]:
            print(f"  - {k}")
        if len(keys) > 10:
            print(f"  ... and {len(keys) - 10} more")
        if not read_df_key and keys:
            for k in keys:
                if k.endswith("/read/df"):
                    read_df_key = k
                    break
        print(f"\nread_df_key for Export/Download: {read_df_key}")
    except httpx.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    _prompt()

    # Step 5: Export
    bytes_key = ""
    export_run_id = ""
    print("\n=== Step 5: Export (filter/map from import) ===")
    if not read_df_key:
        print("No read/df key from Step 3. Export skipped.")
    else:
        try:
            r = httpx.post(
                f"{base}/export/from_artifact",
                data={
                    "source_artifact_key": read_df_key,
                    "entity_key": "demo/excel",
                    "mapping_name": "detect_region_test",
                },
                timeout=60.0,
            )
            r.raise_for_status()
            export_data = r.json()
            export_run_id = export_data.get("run_id", "")
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

    # Step 6: Verify runs, entity_runs, artifacts (before download)
    print("\n=== Step 6: Verify before Download ===")
    print("Confirm download targets exist in runs, entity_runs, artifacts.")
    run_ids_to_show = [rid for rid in (run_id, export_run_id) if rid]
    try:
        all_keys: list[str] = []
        for rid in run_ids_to_show:
            r_runs = httpx.get(f"{base}/runs", params={"run_id": rid}, timeout=10.0)
            if r_runs.status_code == 200 and r_runs.json().get("entries"):
                print(f"runs (run_id={rid}):")
                for rn in r_runs.json()["entries"]:
                    print(f"  - {rn['run_id']} status={rn['status']}")
            r_er = httpx.get(f"{base}/entity_runs", params={"run_id": rid}, timeout=10.0)
            if r_er.status_code == 200 and r_er.json().get("entries"):
                print(f"entity_runs (run_id={rid}):")
                for ent in r_er.json()["entries"]:
                    ap = ent.get("artifact_path") or ""
                    print(f"  - {ent['entity_key']} status={ent['status']} artifact_path={ap}")
            r_art = httpx.get(f"{base}/artifacts", params={"prefix": f"{rid}/"}, timeout=10.0)
            r_art.raise_for_status()
            keys = r_art.json().get("keys", [])
            all_keys.extend(keys)
            print(f"artifacts (prefix={rid}/): {len(keys)} keys")
            for k in keys[:8]:
                print(f"  - {k}")
            if len(keys) > 8:
                print(f"  ... and {len(keys) - 8} more")
            print()
        has_read_df = read_df_key in all_keys or any(k.endswith("/read/df") for k in all_keys)
        has_write_bytes = bytes_key in all_keys or any(k.endswith("/write/bytes") for k in all_keys)
        print(f"read/df present: {has_read_df}")
        print(f"write/bytes present: {has_write_bytes}")
    except httpx.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    _prompt()

    # Step 7: Download
    print("\n=== Step 7: Download ===")
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
