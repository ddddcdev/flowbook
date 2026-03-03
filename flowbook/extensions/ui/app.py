"""
Streamlit demo: hands-on flow via API (Inspect -> Import -> Results -> Export -> Download).

Run with API up:
  uv run uvicorn flowbook.extensions.api.app:app --reload
  uv run flowbook streamlit
"""

from __future__ import annotations

import io
import json
import os
import re

import pandas as pd
import requests
import streamlit as st

from flowbook.core.artifacts.key_utils import build_artifact_key, parse_artifact_key

DEFAULT_BASE = os.environ.get("FLOWBOOK_API_URL", "http://localhost:8000")


def api(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _fetch_input_profile_names(
    base: str, *, inspectable: bool = False
) -> list[str]:
    """Fetch input_profile config names from GET /configs?kind=input_profile.
    When inspectable=True, only profiles with inspect_step_name are returned."""
    try:
        params: dict[str, str | bool] = {"kind": "input_profile"}
        if inspectable:
            params["inspectable"] = True
        r = requests.get(api(base, "/configs"), params=params, timeout=10)
        r.raise_for_status()
        configs = r.json().get("configs", [])
        return [c["name"] for c in configs]
    except requests.RequestException:
        return []


def _filename_from_artifact_key(key: str, fallback: str = "artifact.bin") -> str:
    """Derive download filename from artifact key."""
    parts = key.split("/")
    base = parts[-1] if parts else "artifact"
    safe = re.sub(r'[<>:"|?*\x00-\x1f/\\]', "_", base) or "artifact"
    return f"{safe}.bin" if "." not in safe else safe


def _filename_from_meta(meta: dict | None) -> str | None:
    """Extract filename from meta. Expects meta like {"filename": "demo_excel_exported.xlsx"}."""
    if not meta:
        return None
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            return None
    if not isinstance(meta, dict):
        return None
    fn = meta.get("filename")
    if not isinstance(fn, str) or not fn.strip():
        return None
    safe = re.sub(r'[<>:"|?*\x00-\x1f/\\]', "_", fn.strip()) or None
    return safe


def _download_button(
    content: bytes,
    artifact_key: str,
    widget_key: str,
    filename_override: str | None = None,
) -> None:
    """Render a download button for binary content with filename display."""
    filename = filename_override or _filename_from_artifact_key(artifact_key)
    st.caption(f"Download as: `{filename}`")
    st.download_button(
        label="Download",
        data=content,
        file_name=filename,
        mime="application/octet-stream",
        key=widget_key,
    )


def _entity_key_from_artifact_key(key: str) -> str:
    """Extract entity_key from artifact key {run_id}/{entity_key}/{path}."""
    try:
        _run_id, entity_key, _path = parse_artifact_key(key)
        return entity_key or "default"
    except ValueError:
        return "default"


def _entity_matches(
    entry_entity_key: str | None,
    filter_value: str | None,
    match_mode: str,
) -> bool:
    """Return True if entry matches filter. match_mode: 'exact' or 'partial' (contains)."""
    if filter_value is None or filter_value == "":
        return True
    if entry_entity_key is None:
        return False
    if match_mode == "partial":
        return filter_value in entry_entity_key
    return entry_entity_key == filter_value


def _entity_key_from_entry(entry: dict | object) -> str | None:
    """Extract entity_key from artifact entry (dict or object). Fallback: parse from key."""
    if isinstance(entry, dict):
        ek = entry.get("entity_key")
        if ek is not None and ek != "":
            return ek
        key = entry.get("key")
        if key:
            return _entity_key_from_artifact_key(key)
        return None
    ek = getattr(entry, "entity_key", None)
    if ek is not None and ek != "":
        return ek
    key = getattr(entry, "key", None)
    if key:
        return _entity_key_from_artifact_key(key)
    return None


def _created_at_for_sort(e: object) -> str:
    """Extract created_at for ascending sort. Empty string for missing."""
    if isinstance(e, dict):
        return e.get("created_at") or ""
    return getattr(e, "created_at", None) or ""


def _format_datetime_display(val: str | None) -> str:
    """Format datetime for display: YYYY-MM-DD HH:mm:ss (truncate microseconds)."""
    if not val:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    # Match ISO format: 2026-03-02T21:41:04.123456+09:00 or 2026-03-02T12:36:23.903Z
    m = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})", s)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return s[:19] if len(s) >= 19 else s  # fallback: first 19 chars


def _fetch_inspect_results_from_api(
    base: str,
    entity_key_filter: str | None,
    exact_match: bool = False,
) -> list[dict]:
    """Fetch inspect results from /results and /artifacts APIs. No session_state."""
    try:
        params = {}
        if exact_match and entity_key_filter:
            params["entity_key"] = entity_key_filter
        r = requests.get(api(base, "/results"), params=params or None, timeout=10)
        r.raise_for_status()
        entries = r.json().get("entries", [])
    except requests.RequestException:
        return []
    out = []
    for e in entries:
        cfg = e.get("config_json")
        if not cfg:
            continue
        try:
            cfg_obj = json.loads(cfg) if isinstance(cfg, str) else cfg
        except json.JSONDecodeError:
            continue
        if cfg_obj.get("name") != "inspect" or e.get("status") != "succeeded":
            continue
        ra = e.get("result_artifacts")
        if not ra or not isinstance(ra, list):
            continue
        path_item = ra[0]
        path = path_item.get("path") if isinstance(path_item, dict) else None
        if not path:
            continue
        run_id = e.get("run_id", "")
        entity_key = e.get("entity_key", "")
        key = f"{run_id}/{entity_key}/{path}"
        try:
            r2 = requests.get(api(base, f"/artifacts/{key}/raw"), timeout=10)
            r2.raise_for_status()
            profile = r2.json()
        except (requests.RequestException, json.JSONDecodeError):
            continue
        if not isinstance(profile, dict):
            continue
        if entity_key_filter and not exact_match:
            if not _entity_matches(entity_key, entity_key_filter, "partial"):
                continue
        out.append({
            "run_id": run_id,
            "entity_key": entity_key,
            "profile": profile,
            "created_at": e.get("created_at") or "",
            "updated_at": e.get("updated_at") or "",
        })
    return out[:50]


def _read_df_artifact_key_from_result(entry: dict) -> str | None:
    """Extract read/df artifact key from result entry. Returns None if not found."""
    ra = entry.get("result_artifacts")
    if not ra:
        return None
    if isinstance(ra, str):
        try:
            ra = json.loads(ra)
        except json.JSONDecodeError:
            return None
    if not isinstance(ra, list):
        return None
    run_id = entry.get("run_id", "")
    entity_key = entry.get("entity_key", "")
    for x in ra:
        item = x if isinstance(x, dict) else {"path": str(x)}
        path = item.get("path") if isinstance(item, dict) else None
        if path and "read/df" in path:
            return build_artifact_key(run_id, entity_key, path)
    return None


def _result_entry_for_display(entry: dict) -> dict:
    """Convert result_artifacts to JSON string for readable DataFrame preview."""
    out = dict(entry)
    if "result_artifacts" in out and out["result_artifacts"] is not None:
        out["result_artifacts"] = json.dumps(out["result_artifacts"], ensure_ascii=False)
    for k in ("created_at", "updated_at"):
        if k in out and out[k]:
            out[k] = _format_datetime_display(out[k])
    return out


def _results_preview(base: str, entries: list[dict], event: object) -> None:
    """Show artifact preview when result row is selected (from result_artifacts)."""
    row_idx = None
    sel = getattr(event, "selection", None)
    if sel and getattr(sel, "rows", None):
        row_idx = sel.rows[0]
    if row_idx is None or row_idx >= len(entries):
        return
    entry = entries[row_idx]
    ra = entry.get("result_artifacts")
    if not ra:
        return
    # Parse result_artifacts: list from API or JSON string from display
    if isinstance(ra, str):
        try:
            ra = json.loads(ra)
        except json.JSONDecodeError:
            return
    if not isinstance(ra, list) or not ra:
        return
    # Normalize each item to dict, filter out items without path
    items = []
    for x in ra:
        item = x if isinstance(x, dict) else {"path": str(x)}
        path = item.get("path") if isinstance(item, dict) else None
        if path:
            items.append(item)
    if not items:
        return
    run_id = entry.get("run_id", "")
    entity_key = entry.get("entity_key", "")
    st.subheader(f"{run_id}/{entity_key}")
    tab_labels = [item.get("label") or item.get("path") or str(item) for item in items]
    tabs = st.tabs(tab_labels)
    for i, item in enumerate(items):
        path = item.get("path")
        artifact_key = build_artifact_key(run_id, entity_key, path)
        with tabs[i]:
            st.caption(f"Preview: `{artifact_key}`")
            meta = None
            try:
                meta_resp = requests.get(
                    api(base, f"/artifacts/{artifact_key}"),
                    params={"meta_only": "true"},
                    timeout=10,
                )
                if meta_resp.status_code == 200:
                    meta_val = meta_resp.json().get("value")
                    if isinstance(meta_val, dict):
                        meta = meta_val.get("meta")
            except Exception:
                pass
            raw_content = None
            content_type = None
            try:
                raw_resp = requests.get(api(base, f"/artifacts/{artifact_key}/raw"), timeout=30)
                raw_resp.raise_for_status()
                raw_content = raw_resp.content
                content_type = raw_resp.headers.get("content-type", "").split(";")[0]
            except requests.RequestException:
                pass
            if meta and isinstance(meta, dict):
                st.caption("Meta")
                st.json(meta, expanded=False)
            if raw_content is not None:
                _preview_artifact_content(
                    artifact_key,
                    raw_content,
                    content_type or "",
                    f"dl_results_preview_{i}",
                    meta=meta,
                )


def _preview_artifact_content(
    key: str,
    content: bytes,
    content_type: str | None,
    download_key: str = "dl_preview",
    meta: dict | None = None,
) -> None:
    """Preview artifact content. API response as-is. Download button for octet-stream."""
    if content_type and "octet-stream" in content_type:
        _download_button(content, key, download_key, _filename_from_meta(meta))
    buf = io.BytesIO(content)
    if key.endswith("/read/df"):
        try:
            df = pd.read_parquet(buf)
            st.dataframe(df, width="stretch", hide_index=True)
            return
        except Exception:
            pass
    if (
        key.endswith("/write/bytes")
        or "input/src_excel_bytes" in key
        or (content_type and ("spreadsheet" in content_type or "excel" in content_type))
    ):
        try:
            df = pd.read_excel(buf, engine="openpyxl")
            st.dataframe(df, width="stretch", hide_index=True)
            return
        except Exception:
            pass
    # Try parquet (generic)
    try:
        buf.seek(0)
        df = pd.read_parquet(buf)
        st.dataframe(df, width="stretch", hide_index=True)
        return
    except Exception:
        pass
    # Try JSON (API may return application/json)
    try:
        parsed = json.loads(content.decode("utf-8"))
        if isinstance(parsed, (dict, list)):
            st.json(parsed, expanded=True)
        else:
            st.write(parsed)
        return
    except Exception:
        pass
    # Fallback: text or binary
    try:
        text = content.decode("utf-8", errors="replace")
        if len(text) > 10000:
            st.code(text[:10000] + "\n... (truncated)", language="text")
        else:
            st.code(text, language="text")
    except Exception:
        st.caption(f"Binary ({len(content)} bytes).")


def health(base: str) -> bool:
    try:
        r = requests.get(api(base, "/health"), timeout=5)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


def _entity_key_options(base: str) -> list[str]:
    """Fetch entity_keys from /entities; fallback to latest_results, then demo/excel."""
    try:
        r = requests.get(api(base, "/entities"), timeout=10)
        if r.status_code == 200:
            entries = r.json().get("entries", [])
            keys = sorted(e["entity_key"] for e in entries if e.get("entity_key"))
            if keys:
                return keys
        r = requests.get(api(base, "/latest_results"), timeout=10)
        r.raise_for_status()
        entries = r.json().get("entries", [])
        keys = sorted({e["entity_key"] for e in entries if e.get("entity_key")})
        if "demo/excel" not in keys:
            keys = ["demo/excel"] + keys
        return keys if keys else ["demo/excel"]
    except Exception:
        return ["demo/excel"]


_DEMO_HINT = """Use this app to try the full flow: Inspect → Import → Export → Results → Download.

**Fixtures** (generate if missing):
- Excel: `tests/fixtures/excel/test_detect_region_input.xlsx` (profile `demo_excel_inspect`)
- CSV: `tests/fixtures/csv/demo_input.csv` (profile `demo_csv_inspect`)
→ `flowbook fixture generate -o tests/fixtures/excel --csv-dir tests/fixtures/csv`

**Sequence:**
1. **Inspect** — Upload the file above, entity_key `demo/excel`, profile `demo_excel_inspect`
2. **Import** — Same file, plan `import_excel_simple`, creates read/df artifact
3. **Export** — From Import’s read/df, mapping `detect_region_test`, creates write/bytes
4. **Results** — Select the row with read/df or write/bytes
5. **Download** — Use the selected result’s artifact (as Excel or raw)

Connects to the flowbook API (FastAPI). Use Health tab to verify API is running."""


def main() -> None:
    st.set_page_config(page_title="flowbook", page_icon="📊", layout="wide")
    st.title("flowbook API demo")
    base = st.session_state.get("api_base", DEFAULT_BASE)

    with st.sidebar.popover("About this demo", icon=":material/info:"):
        st.caption(_DEMO_HINT)

    entity_key_opts = _entity_key_options(base)
    custom_keys = st.session_state.get("custom_entity_keys", set())
    opts_set = set(entity_key_opts)
    entity_key_options = entity_key_opts + sorted(k for k in custom_keys if k not in opts_set)
    entity_key = st.sidebar.selectbox(
        "entity_key",
        options=entity_key_options,
        index=None,
        placeholder="Choose an option",
        accept_new_options=True,
        key="sidebar_entity_key",
        help="Scope for Inspect/Import/Export. Filter for Results/Artifacts. Empty = no filter.",
    )
    if entity_key and entity_key not in opts_set:
        custom_keys = custom_keys | {entity_key}
        st.session_state["custom_entity_keys"] = custom_keys
    entity_key_filter_value = entity_key if entity_key else None
    exact_match = st.sidebar.toggle(
        "exact match",
        value=False,
        key="sidebar_entity_exact_match",
        help="ON: exact match, API filter. OFF: partial match (contains), client-side filter.",
    )
    entity_key_for_actions = (
        entity_key if entity_key else (entity_key_opts[0] if entity_key_opts else "demo/excel")
    )

    tab_names = [
        "Health",
        "Inspect",
        "Import",
        "Export",
        "Results",
        "Artifacts",
        "Entities",
        "Configs",
        "Steps",
    ]
    tabs = st.tabs(tab_names)
    tab_health = tabs[0]
    tab_inspect = tabs[1]
    tab_import = tabs[2]
    tab_export = tabs[3]
    tab_results = tabs[4]
    tab_artifacts = tabs[5]
    tab_entities = tabs[6]
    tab_configs = tabs[7]
    tab_steps = tabs[8]

    with tab_health:
        st.subheader("API connection")
        base = st.text_input(
            "API base URL",
            value=DEFAULT_BASE,
            key="api_base",
        )
        if health(base):
            st.success("API OK")
        else:
            st.error(
                "API not reachable. Start: uv run uvicorn flowbook.extensions.api.app:app --reload"
            )

    with tab_steps:
        st.subheader("Steps (ops)")
        st.caption("Select a row to view its spec below.")
        if st.button("Refresh", key="steps_refresh"):
            st.session_state.pop("steps_list", None)
        try:
            r = requests.get(api(base, "/steps"), timeout=10)
            r.raise_for_status()
            ops = r.json().get("ops", [])
            if ops:
                df = pd.DataFrame({"op": ops})
                event = st.dataframe(
                    df,
                    key="steps_df",
                    width="stretch",
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                )
                row_idx = None
                if event.selection and event.selection.rows:
                    row_idx = event.selection.rows[0]
                if row_idx is not None and 0 <= row_idx < len(ops):
                    op_name = ops[row_idx]
                    r2 = requests.get(api(base, f"/steps/{op_name}"), timeout=10)
                    r2.raise_for_status()
                    spec = r2.json()
                    st.subheader(f"Spec: {op_name}")
                    st.markdown(spec.get("docstring") or "(no docstring)")
                    st.caption(
                        "Inputs (required): " + ", ".join(spec.get("required_inputs", []))
                        or "(none)"
                    )
                    st.caption(
                        "Inputs (optional): " + ", ".join(spec.get("optional_inputs", []))
                        or "(none)"
                    )
                    st.caption("Outputs: " + ", ".join(spec.get("output_keys", [])) or "(none)")
            else:
                st.info("No steps. API may not have discover_steps loaded.")
        except requests.RequestException as e:
            st.error(str(e))

    with tab_inspect:
        st.subheader("Inspect (optional)")
        st.caption(
            "Detect kind and effective date from file or filename. "
            "Excel profile (date_rule) requires file upload; CSV profile uses filename only."
        )
        input_profile_opts = _fetch_input_profile_names(base, inspectable=True)
        if not input_profile_opts:
            input_profile_opts = ["demo_excel_inspect", "demo_csv_inspect"]
        input_profile_name = st.selectbox(
            "input_profile",
            options=input_profile_opts,
            key="inspect_input_profile",
        )
        file_inspect = st.file_uploader(
            "Upload file (optional for filename-only profiles)",
            type=["xlsx", "xls", "csv"],
            key="inspect_file",
        )
        filename_inspect = st.text_input(
            "filename (required when file omitted)",
            value="",
            placeholder="e.g. eb-details_2026-01.csv",
            key="inspect_filename",
        )
        can_inspect = file_inspect is not None or (filename_inspect and filename_inspect.strip())
        if can_inspect and st.button("Run inspect", key="inspect_btn"):
            with st.spinner("Inspecting..."):
                try:
                    data_form = {
                        "entity_key": entity_key_for_actions,
                        "input_profile_name": input_profile_name,
                    }
                    if file_inspect:
                        files = {
                            "file": (
                                file_inspect.name,
                                file_inspect.getvalue(),
                                "application/octet-stream",
                            )
                        }
                        r = requests.post(
                            api(base, "/inspect"),
                            files=files,
                            data=data_form,
                            timeout=30,
                        )
                    else:
                        data_form["filename"] = filename_inspect.strip()
                        r = requests.post(
                            api(base, "/inspect"),
                            data=data_form,
                            timeout=30,
                        )
                    r.raise_for_status()
                    data = r.json()
                    profile = data["profile"]
                    st.session_state["inspect_profile"] = profile
                    st.success(f"Run ID: `{data['run_id']}`")
                    st.json(profile)
                    if profile.get("plan_name"):
                        st.caption(f"plan_name: `{profile['plan_name']}`")
                    if profile.get("detected_kind"):
                        st.caption(f"detected_kind: `{profile['detected_kind']}`")
                except requests.RequestException as e:
                    st.error(str(e))

    with tab_import:
        st.subheader("Import (table extract)")
        st.caption(
            "Select an Inspect result to use its parameters. Upload file and run Import."
        )
        if st.button("Refresh", key="import_inspect_refresh"):
            st.rerun()
        inspect_results = _fetch_inspect_results_from_api(
            base, entity_key_filter_value, exact_match
        )
        selected_profile = None
        selected_row_idx = None
        if inspect_results:
            sorted_results = sorted(
                inspect_results,
                key=lambda r: r.get("updated_at") or "",
                reverse=True,
            )
            df_rows = [
                {
                    "updated_at": _format_datetime_display(r.get("updated_at")),
                    "run_id": r.get("run_id") or "",
                    "entity": (r.get("profile") or {}).get("detected_kind")
                    or r.get("entity_key")
                    or "",
                }
                for r in sorted_results
            ]
            df = pd.DataFrame(df_rows)
            event = st.dataframe(
                df,
                key="import_inspect_df",
                width="stretch",
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
            )
            if event.selection and event.selection.rows:
                selected_row_idx = event.selection.rows[0]
                if 0 <= selected_row_idx < len(sorted_results):
                    selected_profile = sorted_results[selected_row_idx].get("profile") or {}
        if selected_profile:
            plan_name = selected_profile.get("plan_name") or "import_excel_simple"
            ek = (
                selected_profile.get("detected_kind")
                if selected_profile.get("detected_kind")
                else entity_key_for_actions
            )
            if plan_name == "import_excel_region":
                inputs_dict = {
                    "entity_key": ek,
                    "sheet_name": "data",
                    "region_profile_name": "detail_region",
                    "mapping_name": "detect_region_test",
                }
            else:
                inputs_dict = {
                    "entity_key": ek,
                    "sheet_name": 0,
                    "header_row": 0,
                }
            st.caption("Import parameters (from selection)")
            st.text_input(
                "plan_name",
                value=plan_name,
                disabled=True,
                key="import_plan_display",
            )
            st.json(inputs_dict)
            inputs_json = json.dumps(inputs_dict)
        else:
            if not inspect_results:
                st.info("No Inspect results. Run Inspect first, then click Refresh.")
            else:
                st.info("Select a row to set import parameters.")
            plan_name = ""
            inputs_json = "{}"
        file = st.file_uploader(
            "Upload file",
            type=["xlsx", "xls", "csv"],
            key="import_file",
        )
        if file and selected_profile and st.button("Run import"):
            with st.spinner("Importing..."):
                try:
                    inputs_dict = json.loads(inputs_json) if inputs_json.strip() else {}
                    r = requests.post(
                        api(base, "/import"),
                        files={
                            "file": (
                                file.name,
                                file.getvalue(),
                                "application/octet-stream",
                            )
                        },
                        data={
                            "plan_name": plan_name,
                            "inputs": json.dumps(inputs_dict),
                        },
                        timeout=60,
                    )
                    r.raise_for_status()
                    data = r.json()
                    st.success(f"Run ID: `{data['run_id']}`")
                    st.json(
                        {
                            "status": data["status"],
                            "artifacts_written": data["artifacts_written"],
                            "errors": data.get("errors", []),
                        }
                    )
                    read_df_keys = [
                        k for k in data.get("artifacts_written", []) if k.endswith("/read/df")
                    ]
                    if read_df_keys:
                        raw_resp = requests.get(
                            api(base, f"/artifacts/{read_df_keys[0]}/raw"),
                            timeout=30,
                        )
                        raw_resp.raise_for_status()
                        df = pd.read_parquet(io.BytesIO(raw_resp.content))
                        st.dataframe(df, width="stretch", hide_index=True)
                except requests.RequestException as e:
                    st.error(str(e))

    with tab_results:
        st.subheader("Results")
        st.caption(
            "Per-run and per-entity results. Export done? Select a row → download below "
            "(Artifact → raw). Postgres only; in-memory returns empty."
        )
        if st.button("Refresh", key="results_refresh"):
            try:
                params = {}
                use_api_filter = exact_match and entity_key_filter_value is not None
                if use_api_filter:
                    params["entity_key"] = entity_key_filter_value
                r = requests.get(api(base, "/results"), params=params or None, timeout=10)
                r.raise_for_status()
                raw_results = r.json().get("entries", [])
                latest_params = {"entity_key": entity_key_filter_value} if use_api_filter else None
                r2 = requests.get(
                    api(base, "/latest_results"),
                    params=latest_params,
                    timeout=10,
                )
                r2.raise_for_status()
                raw_latest = r2.json().get("entries", [])
                if not use_api_filter and entity_key_filter_value is not None:
                    mode = "partial" if not exact_match else "exact"
                    raw_results = [
                        e
                        for e in raw_results
                        if _entity_matches(
                            e.get("entity_key"),
                            entity_key_filter_value,
                            mode,
                        )
                    ]
                    raw_latest = [
                        e
                        for e in raw_latest
                        if _entity_matches(
                            e.get("entity_key"),
                            entity_key_filter_value,
                            mode,
                        )
                    ]
                st.session_state["results"] = raw_results
                st.session_state["latest_results"] = raw_latest
            except requests.RequestException as e:
                st.error(str(e))
        er_entries = st.session_state.get("results", [])
        lat_entries = st.session_state.get("latest_results", [])
        if er_entries or lat_entries:
            show_latest_only = st.toggle(
                "latest_results only (latest per entity_key)",
                value=False,
                key="er_show_latest_only",
            )
            if show_latest_only and lat_entries:
                st.write("**latest_results** (latest per entity_key)")
                entries = lat_entries
                df_key = "latest_results_df"
            else:
                st.write("**results** (full list)")
                entries = er_entries
                df_key = "results_df"
            if entries:
                sorted_entries = sorted(
                    entries,
                    key=lambda e: (_created_at_for_sort(e) == "", _created_at_for_sort(e)),
                )
                df = pd.DataFrame([_result_entry_for_display(e) for e in sorted_entries])
                event = st.dataframe(
                    df,
                    key=df_key,
                    width="stretch",
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                )
                _results_preview(base, sorted_entries, event)
            elif show_latest_only:
                st.info("No latest_results.")
        else:
            st.info("No results. Click Refresh or run Import first.")

    with tab_artifacts:
        st.subheader("List artifacts")
        st.caption("Select a row to preview artifact content. Supports parquet, xlsx, json.")
        if st.button("Refresh list", key="artifacts_refresh"):
            try:
                r = requests.get(api(base, "/artifacts"), timeout=10)
                r.raise_for_status()
                data = r.json()
                keys = data.get("keys", [])
                entries = data.get("entries", [])
                if keys:
                    st.session_state["artifact_keys"] = keys
                    st.session_state["artifact_entries"] = entries
                else:
                    st.info("No artifacts. Run Import first.")
            except requests.RequestException as e:
                st.error(str(e))
        entries = st.session_state.get("artifact_entries", [])
        if entries:
            if entity_key_filter_value is not None:
                mode = "partial" if not exact_match else "exact"
                entries = [
                    e
                    for e in entries
                    if _entity_matches(
                        _entity_key_from_entry(e),
                        entity_key_filter_value,
                        mode,
                    )
                ]
            sorted_entries = sorted(
                entries,
                key=lambda e: (_created_at_for_sort(e) == "", _created_at_for_sort(e)),
            )
            display_entries = []
            for e in sorted_entries:
                d = (
                    dict(e)
                    if isinstance(e, dict)
                    else (e.model_dump() if hasattr(e, "model_dump") else dict(e))
                )
                d.pop("meta", None)
                for k in ("created_at", "updated_at"):
                    if k in d and d[k]:
                        d[k] = _format_datetime_display(d[k])
                display_entries.append(d)
            df = pd.DataFrame(display_entries)
            event = st.dataframe(
                df,
                key="artifacts_df",
                width="stretch",
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
            )
            row_idx = None
            if event.selection and event.selection.rows:
                row_idx = event.selection.rows[0]
            if row_idx is not None and 0 <= row_idx < len(sorted_entries):
                entry = sorted_entries[row_idx]
                key = entry.get("key") if isinstance(entry, dict) else getattr(entry, "key", None)
                if key:
                    st.subheader(f"Preview: `{key}`")
                    meta = (
                        entry.get("meta")
                        if isinstance(entry, dict)
                        else getattr(entry, "meta", None)
                    )
                    if meta is None:
                        try:
                            meta_resp = requests.get(
                                api(base, f"/artifacts/{key}"),
                                params={"meta_only": "true"},
                                timeout=10,
                            )
                            if meta_resp.status_code == 200:
                                meta_val = meta_resp.json().get("value")
                                meta = meta_val.get("meta") if isinstance(meta_val, dict) else None
                        except Exception:
                            pass
                    raw_content = None
                    content_type = None
                    try:
                        raw_resp = requests.get(
                            api(base, f"/artifacts/{key}/raw"),
                            timeout=30,
                        )
                        raw_resp.raise_for_status()
                        raw_content = raw_resp.content
                        content_type = raw_resp.headers.get("content-type", "").split(";")[0]
                    except requests.RequestException:
                        pass
                    if meta and isinstance(meta, dict):
                        st.caption("Meta")
                        st.json(meta, expanded=False)
                    if raw_content is not None:
                        _preview_artifact_content(
                            key,
                            raw_content,
                            content_type or "",
                            "dl_artifacts_preview",
                            meta=meta,
                        )
        elif "artifact_keys" in st.session_state:
            st.caption("Keys available. Click Refresh list to load.")

    with tab_export:
        st.subheader("Export (filter/map -> xlsx)")
        st.caption("Select a result row (import with read/df). Entity filter from sidebar.")
        if st.button("Load results", key="export_load"):
            try:
                params = {}
                use_api_filter = exact_match and entity_key_filter_value is not None
                if use_api_filter:
                    params["entity_key"] = entity_key_filter_value
                r = requests.get(api(base, "/results"), params=params or None, timeout=10)
                r.raise_for_status()
                raw_results = r.json().get("entries", [])
                latest_params = {"entity_key": entity_key_filter_value} if use_api_filter else None
                r2 = requests.get(
                    api(base, "/latest_results"),
                    params=latest_params,
                    timeout=10,
                )
                r2.raise_for_status()
                raw_latest = r2.json().get("entries", [])
                if not use_api_filter and entity_key_filter_value is not None:
                    mode = "partial" if not exact_match else "exact"
                    raw_results = [
                        e
                        for e in raw_results
                        if _entity_matches(
                            e.get("entity_key"),
                            entity_key_filter_value,
                            mode,
                        )
                    ]
                    raw_latest = [
                        e
                        for e in raw_latest
                        if _entity_matches(
                            e.get("entity_key"),
                            entity_key_filter_value,
                            mode,
                        )
                    ]
                st.session_state["results"] = raw_results
                st.session_state["latest_results"] = raw_latest
                st.rerun()
            except requests.RequestException as e:
                st.error(str(e))
        er_entries = st.session_state.get("results", [])
        lat_entries = st.session_state.get("latest_results", [])
        if not er_entries and not lat_entries:
            st.info("Click Load results or run Import first.")
        else:
            # Export needs import results (read/df). Filter from full results.
            entries_with_df = [
                e for e in er_entries if _read_df_artifact_key_from_result(e) is not None
            ]
            if not entries_with_df:
                st.info(
                    "No import results (read/df) in the list. Run Import first, then Load results."
                )
            else:
                show_latest = st.toggle(
                    "latest per entity (imports with read/df only)",
                    value=True,
                    key="export_show_latest",
                )
                if show_latest:
                    # Keep latest (max updated_at) per entity_key
                    by_entity: dict[str, dict] = {}
                    for e in entries_with_df:
                        ek = e.get("entity_key", "")
                        if not ek:
                            continue
                        cur = by_entity.get(ek)
                        if cur is None or _created_at_for_sort(e) > _created_at_for_sort(cur):
                            by_entity[ek] = e
                    entries = list(by_entity.values())
                else:
                    entries = entries_with_df
                if entries:
                    sorted_entries = sorted(
                        entries,
                        key=lambda e: (_created_at_for_sort(e) == "", _created_at_for_sort(e)),
                    )
                    df = pd.DataFrame([_result_entry_for_display(e) for e in sorted_entries])
                    event = st.dataframe(
                        df,
                        key="export_results_df",
                        width="stretch",
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="single-row",
                    )
                    row_idx = None
                    sel = getattr(event, "selection", None)
                    if sel and getattr(sel, "rows", None):
                        row_idx = sel.rows[0]
                    if row_idx is not None and row_idx < len(sorted_entries):
                        selected = sorted_entries[row_idx]
                        source_key = _read_df_artifact_key_from_result(selected)
                        export_entity = selected.get("entity_key", "")
                        st.caption(f"Selected: `{source_key}`")
                        if st.button("Run export", key="export_run"):
                            with st.spinner("Exporting..."):
                                try:
                                    r = requests.post(
                                        api(base, "/export/from_artifact"),
                                        data={
                                            "source_artifact_key": source_key,
                                            "entity_key": export_entity,
                                            "mapping_name": "detect_region_test",
                                        },
                                        timeout=60,
                                    )
                                    r.raise_for_status()
                                    data = r.json()
                                    written = data.get("artifacts_written", [])
                                    bytes_keys = [k for k in written if "/write/bytes" in k]
                                    if bytes_keys:
                                        st.success(
                                            "Export done. Download via Results tab "
                                            "(select row → download)."
                                        )
                                        if "artifact_keys" not in st.session_state:
                                            st.session_state["artifact_keys"] = []
                                        st.session_state["artifact_keys"] = list(
                                            set(st.session_state["artifact_keys"] + written)
                                        )
                                        raw_resp = requests.get(
                                            api(base, f"/artifacts/{bytes_keys[0]}/raw"),
                                            timeout=30,
                                        )
                                        raw_resp.raise_for_status()
                                        try:
                                            df_out = pd.read_excel(
                                                io.BytesIO(raw_resp.content),
                                                engine="openpyxl",
                                            )
                                            st.dataframe(
                                                df_out,
                                                width="stretch",
                                                hide_index=True,
                                            )
                                        except ImportError:
                                            st.warning(
                                                "Preview requires openpyxl. "
                                                "Download via Artifacts tab."
                                            )
                                    st.json(
                                        {
                                            "status": data["status"],
                                            "artifacts_written": written,
                                        }
                                    )
                                except requests.RequestException as e:
                                    st.error(str(e))
                    else:
                        st.caption("Select a row to export.")

    with tab_entities:
        st.subheader("Entities")
        st.caption(
            "Registered entities (entity_key, meta). Postgres only; in-memory returns empty."
        )
        if st.button("Refresh", key="entities_refresh"):
            try:
                r = requests.get(api(base, "/entities"), timeout=10)
                r.raise_for_status()
                data = r.json()
                st.session_state["entities_list"] = data.get("entries", [])
            except requests.RequestException as e:
                st.error(str(e))
        entries = st.session_state.get("entities_list", [])
        if entries:
            df = pd.DataFrame(
                [
                    {
                        "entity_key": e.get("entity_key", ""),
                        "display_name": (e.get("meta") or {}).get("display_name", ""),
                        "desc": (e.get("meta") or {}).get("desc", ""),
                        "created_at": _format_datetime_display(e.get("created_at")),
                        "updated_at": _format_datetime_display(e.get("updated_at")),
                    }
                    for e in entries
                ]
            )
            st.dataframe(df, width="stretch", hide_index=True)
        else:
            st.info("No entities. Click Refresh or run Import to auto-register entities.")

    with tab_configs:
        st.subheader("Configs (input_profiles, mappings, plans, entity_plan_maps)")
        if st.button("Refresh list", key="configs_refresh"):
            try:
                r = requests.get(api(base, "/configs"), timeout=10)
                r.raise_for_status()
                data = r.json()
                st.session_state["configs_list"] = data.get("configs", [])
            except requests.RequestException as e:
                st.error(str(e))
        configs_list = st.session_state.get("configs_list", [])
        if configs_list:
            st.caption("Select a row to view its spec below.")
            df = pd.DataFrame(configs_list)
            event = st.dataframe(
                df,
                key="configs_df",
                width="stretch",
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
            )
            row_idx = None
            if event.selection and event.selection.rows:
                row_idx = event.selection.rows[0]
            if row_idx is not None and 0 <= row_idx < len(configs_list):
                c = configs_list[row_idx]
                kind, name = c["kind"], c["name"]
                try:
                    r = requests.get(api(base, f"/configs/{kind}/{name}"), timeout=10)
                    r.raise_for_status()
                    st.subheader(f"Spec: {kind} / {name}")
                    st.json(r.json().get("spec", {}))
                except requests.RequestException as e:
                    st.error(str(e))
        else:
            if "configs_list" in st.session_state and not configs_list:
                st.info(
                    "No configs. Run reset_db.py / seed_configs_from_dir.py to seed from configs/."
                )
            else:
                st.caption("Click «Refresh list» to load configs from the API.")


if __name__ == "__main__":
    main()
