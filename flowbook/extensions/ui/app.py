"""
Streamlit demo: call flowbook API (Import -> List -> Export -> Download).

Run with API up:
  poetry run uvicorn flowbook.extensions.api.app:app --reload
  poetry run streamlit run flowbook/extensions/ui/app.py
"""

from __future__ import annotations

import io

import pandas as pd
import requests
import streamlit as st

DEFAULT_BASE = "http://localhost:8000"


def api(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def health(base: str) -> bool:
    try:
        r = requests.get(api(base, "/health"), timeout=5)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


def main() -> None:
    st.set_page_config(page_title="flowbook", page_icon="📊", layout="wide")
    st.title("flowbook API demo")
    base = st.sidebar.text_input(
        "API base URL",
        value=DEFAULT_BASE,
    )
    if not health(base):
        st.sidebar.error(
            "API not reachable. Start: poetry run uvicorn flowbook.extensions.api.app:app --reload"
        )
    else:
        st.sidebar.success("API OK")

    tab_inspect, tab_import, tab_artifacts, tab_export, tab_download, tab_configs = st.tabs(
        ["Inspect", "Import", "Artifacts", "Export", "Download", "Configs"]
    )

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
                        data={"input_profile_name": "source"},
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
                        st.dataframe(df, use_container_width=True, hide_index=True)
                except requests.RequestException as e:
                    st.error(str(e))

    with tab_artifacts:
        st.subheader("List artifacts")
        if st.button("Refresh list"):
            try:
                r = requests.get(api(base, "/artifacts"), timeout=10)
                r.raise_for_status()
                data = r.json()
                keys = data.get("keys", [])
                if keys:
                    st.dataframe(
                        data.get("entries", []),
                        use_container_width=True,
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
            if st.button("Run export"):
                with st.spinner("Exporting..."):
                    try:
                        r = requests.post(
                            api(base, "/export/from_artifact"),
                            data={
                                "source_artifact_key": source,
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
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        st.json({"status": data["status"], "artifacts_written": written})
                    except requests.RequestException as e:
                        st.error(str(e))

    with tab_download:
        st.subheader("Download artifact")
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
                file_name = "imported.xlsx"
            else:
                suffix = "raw"
                label = "Download raw (exported xlsx or parquet)"
                file_name = "exported.xlsx"
            url = api(base, f"/artifacts/{key}/{suffix}")
            if st.button("Prepare download", key="prepare_dl"):
                with st.spinner("Fetching..."):
                    try:
                        r = requests.get(url, timeout=30)
                        r.raise_for_status()
                        st.session_state["dl_bytes"] = r.content
                        st.session_state["dl_file_name"] = file_name
                        st.session_state["dl_mime"] = (
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            if suffix == "as_excel"
                            else "application/octet-stream"
                        )
                        st.success("Ready. Click the download button below.")
                    except requests.RequestException as e:
                        st.error(str(e))
            if "dl_bytes" in st.session_state and st.session_state.get("dl_file_name") == file_name:
                st.download_button(
                    label=label,
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
                use_container_width=True,
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
