"""Interactive hands-on: Health -> Inspect -> Import -> Verify -> Export -> Verify -> Download."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import httpx

_console = None


def _get_console():
    """Lazy-init Rich Console when available. Returns None if Rich not installed."""
    global _console
    if _console is not None:
        return _console
    try:
        from rich.console import Console

        _console = Console(force_terminal=True)
        return _console
    except ImportError:
        _console = False
        return None


def _fmt_result_artifacts(ra: list) -> str:
    """Format result_artifacts for display."""
    if not ra:
        return "(none)"
    parts = [f"{x['path']}" + (f" ({x['label']})" if x.get("label") else "") for x in ra]
    return ", ".join(parts)


def _print_json(data: object) -> None:
    """Print JSON with Rich syntax highlighting when available."""
    con = _get_console()
    if con:
        con.print_json(data=data)
    else:
        print(json.dumps(data, indent=2))


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

    # Optional: full init (reset artifacts, results, runs, entities, configs;
    # seed demo entities + configs)
    run_reset = False
    if interactive:
        init_ans = input("Full init DB (clear artifacts + configs, then seed)? [Y/n] ").strip()
        run_reset = init_ans.lower() != "n"
        if not run_reset:
            print("Skipping init.")
    else:
        # Run-through: always reset so state matches flowbook db reset
        run_reset = True

    if run_reset:
        from flowbook.extensions.cli.db import reset_db

        if os.environ.get("FLOWBOOK_DB_RESET") != "1":
            os.environ["FLOWBOOK_DB_RESET"] = "1"
        code = reset_db(config_dir)
        if code != 0:
            return code
        if interactive:
            _prompt()

    # Step 1: Health
    print("\n=== Step 1: Health ===")
    try:
        r = httpx.get(f"{base}/health", timeout=10.0)
        r.raise_for_status()
        _print_json(r.json())
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
        _print_json(r.json())
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
        _print_json(import_data)
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

    # Step 4: Verify runs, results, artifacts (created by import)
    print("\n=== Step 4: Verify runs, results, artifacts ===")
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
        # results for this run (Postgres only; InMemory returns empty)
        r_er = httpx.get(f"{base}/results", params={"run_id": run_id}, timeout=10.0)
        if r_er.status_code == 200 and r_er.json().get("entries"):
            print("results (this run) - result_artifacts = main result paths from plan:")
            for ent in r_er.json()["entries"]:
                ra = ent.get("result_artifacts") or []
                ri, ek, st = ent["run_id"], ent["entity_key"], ent["status"]
                ra_str = _fmt_result_artifacts(ra)
                print(f"  - {ri}/{ek} status={st} result_artifacts=[{ra_str}]")
            # Get details to confirm result_artifacts
            r_er_get = httpx.get(f"{base}/results/{run_id}/{entity_key}", timeout=10.0)
            if r_er_get.status_code == 200:
                detail = r_er_get.json()
                ra = detail.get("result_artifacts") or []
                ap = ra[0]["path"] if ra else None
                if ap:
                    read_df_key = f"{run_id}/{entity_key}/{ap}"
                    print(f"  -> read_df_key from result result_artifacts[0]: {read_df_key}")
        else:
            print("results: (empty or not available; using import response)")
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
            _print_json(export_data)
            print(f"\nwrite/bytes key (exported): {bytes_key}")
        except httpx.HTTPError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    _prompt()

    # Step 6: Verify runs, results, artifacts (before download)
    print("\n=== Step 6: Verify before Download ===")
    print("Confirm download targets exist in runs, results, artifacts.")
    run_ids_to_show = [rid for rid in (run_id, export_run_id) if rid]
    try:
        all_keys: list[str] = []
        for rid in run_ids_to_show:
            r_runs = httpx.get(f"{base}/runs", params={"run_id": rid}, timeout=10.0)
            if r_runs.status_code == 200 and r_runs.json().get("entries"):
                print(f"runs (run_id={rid}):")
                for rn in r_runs.json()["entries"]:
                    print(f"  - {rn['run_id']} status={rn['status']}")
            r_er = httpx.get(f"{base}/results", params={"run_id": rid}, timeout=10.0)
            if r_er.status_code == 200 and r_er.json().get("entries"):
                print(f"results (run_id={rid}):")
                for ent in r_er.json()["entries"]:
                    ra = ent.get("result_artifacts") or []
                    ra_str = _fmt_result_artifacts(ra)
                    ek, st = ent["entity_key"], ent["status"]
                    print(f"  - {ek} status={st} result_artifacts=[{ra_str}]")
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

    def _filename_from_response(r: httpx.Response, fallback: str) -> str:
        cd = r.headers.get("content-disposition")
        if not cd or "filename=" not in cd:
            return fallback
        # Parse filename="..." or filename*=UTF-8''...
        m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\s]+)', cd, re.I)
        return m.group(1).strip() if m else fallback

    if read_df_key:
        try:
            r = httpx.get(f"{base}/artifacts/{read_df_key}/as_excel", timeout=60.0)
            r.raise_for_status()
            fname = _filename_from_response(r, "demo_imported.xlsx")
            out = Path(fname)
            out.write_bytes(r.content)
            print(f"Saved imported: {out}")
        except httpx.HTTPError as e:
            print(f"Download error: {e}", file=sys.stderr)
    if bytes_key:
        try:
            r = httpx.get(f"{base}/artifacts/{bytes_key}/raw", timeout=60.0)
            r.raise_for_status()
            fname = _filename_from_response(r, "demo_exported.xlsx")
            out = Path(fname)
            out.write_bytes(r.content)
            print(f"Saved exported: {out}")
        except httpx.HTTPError as e:
            print(f"Download error: {e}", file=sys.stderr)
    if not read_df_key and not bytes_key:
        print("Could not determine keys. Download manually.")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
