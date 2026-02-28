"""
Streamlit demo: hands-on flow via API (Inspect -> Import -> Entity runs -> Export -> Download).

Run with API up:
  uv run uvicorn flowbook.extensions.api.app:app --reload
  uv run flowbook streamlit
"""

from __future__ import annotations

import io
import os
import re

import pandas as pd
import requests
import streamlit as st

from flowbook.core.artifacts.key_utils import parse_artifact_key

DEFAULT_BASE = os.environ.get("FLOWBOOK_API_URL", "http://localhost:8000")


def api(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _filename_from_response(r: requests.Response, fallback: str) -> str:
    """Extract filename from Content-Disposition header."""
    cd = r.headers.get("content-disposition")
    if not cd or "filename=" not in cd:
        return fallback
    m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\s]+)', cd, re.I)
    return m.group(1).strip() if m else fallback


def _entity_key_from_artifact_key(key: str) -> str:
    """Extract entity_key from artifact key {run_id}/{entity_key}/{path}."""
    try:
        _run_id, entity_key, _path = parse_artifact_key(key)
        return entity_key or "default"
    except ValueError:
        return "default"


def health(base: str) -> bool:
    try:
        r = requests.get(api(base, "/health"), timeout=5)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


def _entity_key_options(base: str) -> list[str]:
    """Fetch registered entity_keys from latest_entity_runs; fallback to demo/excel."""
    try:
        r = requests.get(api(base, "/latest_entity_runs"), timeout=10)
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

    tab_names = [
        "Steps", "Inspect", "Import", "Entity runs", "Artifacts", "Export", "Download",
        "Configs",
    ]
    tabs = st.tabs(tab_names)
    tab_steps = tabs[0]
    tab_inspect = tabs[1]
    tab_import = tabs[2]
    tab_entity_runs = tabs[3]
    tab_artifacts = tabs[4]
    tab_export = tabs[5]
    tab_download = tabs[6]
    tab_configs = tabs[7]

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
        entity_key_inspect = st.selectbox(
            "entity_key", options=entity_key_opts, key="inspect_entity_key"
        )
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
                            "entity_key": entity_key_inspect,
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
        entity_key_import = st.selectbox(
            "entity_key", options=entity_key_opts, key="import_entity_key"
        )
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
                            "entity_key": entity_key_import,
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

    with tab_entity_runs:
        st.subheader("Entity runs")
        st.caption("Per-run and per-entity results. Postgres only; in-memory returns empty.")
        run_id_filter = st.text_input("Filter by run_id", key="er_run_id", placeholder="optional")
        entity_key_filter = st.text_input(
            "Filter by entity_key", key="er_entity_key", placeholder="optional"
        )
        if st.button("Refresh", key="entity_runs_refresh"):
            try:
                params = {}
                if run_id_filter.strip():
                    params["run_id"] = run_id_filter.strip()
                if entity_key_filter.strip():
                    params["entity_key"] = entity_key_filter.strip()
                r = requests.get(api(base, "/entity_runs"), params=params or None, timeout=10)
                r.raise_for_status()
                st.session_state["entity_runs"] = r.json().get("entries", [])
                latest_params = (
                    {"entity_key": entity_key_filter.strip()}
                    if entity_key_filter.strip()
                    else None
                )
                r2 = requests.get(
                    api(base, "/latest_entity_runs"),
                    params=latest_params,
                    timeout=10,
                )
                r2.raise_for_status()
                st.session_state["latest_entity_runs"] = r2.json().get("entries", [])
            except requests.RequestException as e:
                st.error(str(e))
        er_entries = st.session_state.get("entity_runs", [])
        lat_entries = st.session_state.get("latest_entity_runs", [])
        if er_entries:
            st.write("**entity_runs** (by run_id)")
            df_er = pd.DataFrame(er_entries)
            st.dataframe(df_er, width="stretch", hide_index=True)
        else:
            st.info("No entity_runs. Click Refresh or run Import first.")
        if lat_entries:
            st.write("**latest_entity_runs** (latest per entity_key)")
            df_lat = pd.DataFrame(lat_entries)
            st.dataframe(df_lat, width="stretch", hide_index=True)

    with tab_artifacts:
        st.subheader("List artifacts")
        st.caption("Artifact keys for Export (read/df) and Download.")
        if st.button("Refresh list"):
            try:
                r = requests.get(api(base, "/artifacts"), timeout=10)
                r.raise_for_status()
                data = r.json()
                keys = data.get("keys", [])
                if keys:
                    st.dataframe(
                        data.get("entries", []),
                        width="stretch",
                        hide_index=True,
                    )
                    st.session_state["artifact_keys"] = keys
                else:
                    st.info("No artifacts. Run Import first.")
            except requests.RequestException as e:
                st.error(str(e))
        if "artifact_keys" in st.session_state:
            st.caption("Keys available for Export (use read/df) or Download below.")

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
            export_opts = (
                [inferred] + [k for k in entity_key_opts if k != inferred]
                if inferred not in entity_key_opts
                else entity_key_opts
            )
            default_idx = 0 if inferred not in entity_key_opts else entity_key_opts.index(inferred)
            entity_key_export = st.selectbox(
                "entity_key",
                options=export_opts,
                index=default_idx,
                key="export_entity_key",
            )
            if st.button("Run export"):
                with st.spinner("Exporting..."):
                    try:
                        r = requests.post(
                            api(base, "/export/from_artifact"),
                            data={
                                "source_artifact_key": source,
                                "entity_key": entity_key_export,
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

    with tab_download:
        st.subheader("Download artifact")
        st.caption("Pick artifact; filename comes from Content-Disposition (entity_key-based).")
        keys = st.session_state.get("artifact_keys", [])
        if not keys:
            if st.button("Load keys to download"):
                try:
                    r = requests.get(api(base, "/artifacts"), timeout=10)
                    r.raise_for_status()
                    keys = r.json().get("keys", [])
                    st.session_state["artifact_keys"] = keys
                    st.rerun()
                except requests.RequestException as e:
                    st.error(str(e))
            else:
                st.info("No keys. List artifacts or run Import/Export first.")
        else:
            key = st.selectbox("Artifact key", options=keys, key="dl_key")
            if key.endswith("/read/df"):
                suffix = "as_excel"
                label = "Download as Excel (imported table)"
                fallback_name = "imported.xlsx"
            else:
                suffix = "raw"
                label = "Download raw (exported xlsx or parquet)"
                fallback_name = "exported.xlsx"
            url = api(base, f"/artifacts/{key}/{suffix}")
            if st.button("Prepare download", key="prepare_dl"):
                with st.spinner("Fetching..."):
                    try:
                        r = requests.get(url, timeout=30)
                        r.raise_for_status()
                        file_name = _filename_from_response(r, fallback_name)
                        st.session_state["dl_key"] = key
                        st.session_state["dl_bytes"] = r.content
                        st.session_state["dl_file_name"] = file_name
                        st.session_state["dl_mime"] = (
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            if suffix == "as_excel"
                            else "application/octet-stream"
                        )
                        st.session_state["dl_label"] = label
                        st.success("Ready. Click the download button below.")
                    except requests.RequestException as e:
                        st.error(str(e))
            if (
                "dl_bytes" in st.session_state
                and st.session_state.get("dl_key") == key
            ):
                st.download_button(
                    label=st.session_state.get("dl_label", label),
                    data=st.session_state["dl_bytes"],
                    file_name=st.session_state["dl_file_name"],
                    mime=st.session_state["dl_mime"],
                    key="dl_btn",
                )
            st.caption(f"URL: `{url}` (open in browser or use curl).")

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
