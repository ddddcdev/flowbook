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


def _result_entry_for_display(entry: dict) -> dict:
    """Convert result_artifacts to JSON string for readable DataFrame preview."""
    out = dict(entry)
    if "result_artifacts" in out and out["result_artifacts"] is not None:
        out["result_artifacts"] = json.dumps(out["result_artifacts"], ensure_ascii=False)
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
    first = ra[0] if isinstance(ra[0], dict) else {"path": str(ra[0])}
    path = first.get("path") if isinstance(first, dict) else None
    if not path:
        return
    run_id = entry.get("run_id", "")
    entity_key = entry.get("entity_key", "")
    artifact_key = build_artifact_key(run_id, entity_key, path)
    st.subheader(f"Preview: `{artifact_key}`")
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
        raw_resp = requests.get(
            api(base, f"/artifacts/{artifact_key}/raw"), timeout=30
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
            artifact_key,
            raw_content,
            content_type or "",
            "dl_results_preview",
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
    """Fetch registered entity_keys from latest_results; fallback to demo/excel."""
    try:
        r = requests.get(api(base, "/latest_results"), timeout=10)
        r.raise_for_status()
        entries = r.json().get("entries", [])
        keys = sorted({e["entity_key"] for e in entries if e.get("entity_key")})
        if "demo/excel" not in keys:
            keys = ["demo/excel"] + keys
        return keys if keys else ["demo/excel"]
    except Exception:
        return ["demo/excel"]


def main() -> None:
    st.set_page_config(page_title="flowbook", page_icon="📊", layout="wide")
    st.title("flowbook API demo")
    base = st.sidebar.text_input(
        "API base URL",
        value=DEFAULT_BASE,
    )
    if not health(base):
        st.sidebar.error(
            "API not reachable. Start: uv run uvicorn flowbook.extensions.api.app:app --reload"
        )
    else:
        st.sidebar.success("API OK")

    entity_key_opts = _entity_key_options(base)
    custom_keys = st.session_state.get("custom_entity_keys", set())
    opts_set = set(entity_key_opts)
    entity_key_options = entity_key_opts + sorted(
        k for k in custom_keys if k not in opts_set
    )
    entity_key = st.sidebar.selectbox(
        "entity_key",
        options=entity_key_options,
        index=None,
        placeholder="Choose an option",
        accept_new_options=True,
        key="sidebar_entity_key",
    )
    if entity_key and entity_key not in opts_set:
        custom_keys = custom_keys | {entity_key}
        st.session_state["custom_entity_keys"] = custom_keys
    exact_match = st.sidebar.toggle(
        "exact match",
        value=True,
        key="sidebar_entity_exact_match",
        help="ON: exact match, API filter. OFF: partial match (contains), client-side filter.",
    )
    entity_key_filter_value = entity_key
    entity_key_for_actions = (
        entity_key
        if entity_key is not None
        else (entity_key_opts[0] if entity_key_opts else "demo/excel")
    )

    tab_names = [
        "Inspect", "Import", "Export", "Artifacts", "Results",
        "Configs", "Steps",
    ]
    tabs = st.tabs(tab_names)
    tab_inspect = tabs[0]
    tab_import = tabs[1]
    tab_export = tabs[2]
    tab_artifacts = tabs[3]
    tab_results = tabs[4]
    tab_configs = tabs[5]
    tab_steps = tabs[6]

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
                        "Inputs (required): "
                        + ", ".join(spec.get("required_inputs", []))
                        or "(none)"
                    )
                    st.caption(
                        "Inputs (optional): "
                        + ", ".join(spec.get("optional_inputs", []))
                        or "(none)"
                    )
                    st.caption(
                        "Outputs: " + ", ".join(spec.get("output_keys", [])) or "(none)"
                    )
            else:
                st.info("No steps. API may not have discover_steps loaded.")
        except requests.RequestException as e:
            st.error(str(e))

    with tab_inspect:
        st.subheader("Inspect Excel (optional)")
        st.caption("Detect kind and effective date from the uploaded xlsx before import.")
        file_inspect = st.file_uploader("Upload xlsx", type=["xlsx", "xls"], key="inspect_file")
        if file_inspect and st.button("Run inspect", key="inspect_btn"):
            with st.spinner("Inspecting..."):
                try:
                    r = requests.post(
                        api(base, "/inspect"),
                        files={
                            "file": (
                                file_inspect.name,
                                file_inspect.getvalue(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        },
                        data={
                            "entity_key": entity_key_for_actions,
                            "input_profile_name": "source",
                        },
                        timeout=30,
                    )
                    r.raise_for_status()
                    data = r.json()
                    st.success(f"Run ID: `{data['run_id']}`")
                    st.json(data["profile"])
                except requests.RequestException as e:
                    st.error(str(e))

    with tab_import:
        st.subheader("Import Excel (table extract)")
        st.caption("Upload xlsx, set entity_key (e.g. demo/excel). Creates read/df artifact.")
        file = st.file_uploader("Upload xlsx", type=["xlsx", "xls"], key="import_file")
        if file and st.button("Run import"):
            with st.spinner("Importing..."):
                try:
                    r = requests.post(
                        api(base, "/import"),
                        files={
                            "file": (
                                file.name,
                                file.getvalue(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        },
                        data={
                            "template_name": "import_excel_region",
                            "entity_key": entity_key_for_actions,
                            "input_profile_name": "source",
                            "sheet_name": "data",
                            "header_row": 0,
                            "header_col": 0,
                            "region_profile_name": "detail_region",
                            "mapping_name": "detect_region_test",
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
        st.caption("Per-run and per-entity results. Postgres only; in-memory returns empty.")
        run_id_filter = st.text_input("Filter by run_id", key="er_run_id", placeholder="optional")
        if st.button("Refresh", key="results_refresh"):
            try:
                params = {}
                if run_id_filter.strip():
                    params["run_id"] = run_id_filter.strip()
                use_api_filter = (
                    exact_match and entity_key_filter_value is not None
                )
                if use_api_filter:
                    params["entity_key"] = entity_key_filter_value
                r = requests.get(api(base, "/results"), params=params or None, timeout=10)
                r.raise_for_status()
                raw_results = r.json().get("entries", [])
                latest_params = (
                    {"entity_key": entity_key_filter_value}
                    if use_api_filter
                    else None
                )
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
                                meta = (
                                    meta_val.get("meta")
                                    if isinstance(meta_val, dict)
                                    else None
                                )
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
                        content_type = raw_resp.headers.get(
                            "content-type", ""
                        ).split(";")[0]
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
        st.caption("Pick read/df artifact, set entity_key. Creates write/bytes (xlsx).")
        keys = st.session_state.get("artifact_keys", [])
        df_keys = [k for k in keys if k.endswith("/read/df")]
        if not df_keys:
            if st.button("Load keys for export"):
                try:
                    r = requests.get(api(base, "/artifacts"), timeout=10)
                    r.raise_for_status()
                    keys = r.json().get("keys", [])
                    df_keys = [k for k in keys if k.endswith("/read/df")]
                    st.session_state["artifact_keys"] = keys
                    st.rerun()
                except requests.RequestException as e:
                    st.error(str(e))
            else:
                st.info("No import keys. List artifacts first or run Import.")
        else:
            source = st.selectbox("Source artifact (read/df)", options=df_keys, key="export_source")
            inferred = _entity_key_from_artifact_key(source)
            st.caption(f"Inferred from source: `{inferred}` (entity from sidebar)")
            if st.button("Run export"):
                with st.spinner("Exporting..."):
                    try:
                        r = requests.post(
                            api(base, "/export/from_artifact"),
                            data={
                                "source_artifact_key": source,
                                "entity_key": entity_key_for_actions,
                                "mapping_name": "detect_region_test",
                            },
                            timeout=60,
                        )
                        r.raise_for_status()
                        data = r.json()
                        written = data.get("artifacts_written", [])
                        bytes_keys = [k for k in written if "/write/bytes" in k]
                        if bytes_keys:
                            st.success("Export done. Download below (Artifact -> raw).")
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
                            df = pd.read_excel(io.BytesIO(raw_resp.content), engine="openpyxl")
                            st.dataframe(df, width="stretch", hide_index=True)
                        st.json({"status": data["status"], "artifacts_written": written})
                    except requests.RequestException as e:
                        st.error(str(e))

    with tab_configs:
        st.subheader("Configs (input_profiles, mappings, templates, routing)")
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
