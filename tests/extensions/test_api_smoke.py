"""
Smoke test for the FastAPI sample app.

Verifies:
- /health returns 200
- POST /inspect with an Excel file returns a profile
- POST /import with a file + plan executes a plan
- POST /export with bindings executes an export plan
- GET /artifacts lists keys; GET /artifacts/{key} retrieves value
- Failure responses include run_id + reason
"""

from __future__ import annotations

import json
import os
import uuid
from io import BytesIO

import openpyxl
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from flowbook.core.configs.spec_types import InputProfile, Plan
from flowbook.extensions.api.app import app
from flowbook.extensions.api.deps import get_engine

pytestmark = pytest.mark.smoke

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---- fixtures ----


@pytest.fixture(autouse=True)
def _reset_engine():
    """Clear the cached engine between tests."""
    get_engine.cache_clear()
    yield
    get_engine.cache_clear()


@pytest.fixture(scope="session" if os.environ.get("FLOWBOOK_DATABASE_URL") else "function")
def client() -> TestClient:
    """Seed config store with test configs, then return a TestClient.
    Session scope when Postgres: avoids duplicate config rows from repeated put_spec."""
    engine = get_engine()
    assert engine.config_store is not None

    # InputProfile for inspect
    engine.config_store.put_spec(
        InputProfile,
        "demo_excel_inspect",
        {
            "kind_rules": [
                {"pattern": r"^fileA_.*\.xlsx$", "kind": "fileA"},
            ],
            "inspect_step_name": "inspect_excel_bytes_v2",
        },
        config_id=str(uuid.uuid4()),
    )

    # Plan for import: read excel bytes → df artifact
    engine.config_store.put_spec(
        Plan,
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
                ],
            }
        },
        config_id=str(uuid.uuid4()),
    )

    # Plan for export: write DataFrame to Excel bytes
    engine.config_store.put_spec(
        Plan,
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
                ],
            }
        },
        config_id=str(uuid.uuid4()),
    )

    return TestClient(app)


@pytest.fixture()
def client_in_memory(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Force in-memory store for tests that verify empty runs/results/entities.
    Unsets FLOWBOOK_DATABASE_URL so Postgres does not persist data across tests."""
    monkeypatch.delenv("FLOWBOOK_DATABASE_URL", raising=False)
    get_engine.cache_clear()
    engine = get_engine()
    assert engine.config_store is not None
    engine.config_store.put_spec(
        InputProfile,
        "demo_excel_inspect",
        {
            "kind_rules": [{"pattern": r"^fileA_.*\.xlsx$", "kind": "fileA"}],
            "inspect_step_name": "inspect_excel_bytes_v2",
        },
        config_id=str(uuid.uuid4()),
    )
    engine.config_store.put_spec(
        Plan,
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
                ],
            }
        },
        config_id=str(uuid.uuid4()),
    )
    engine.config_store.put_spec(
        Plan,
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
                ],
            }
        },
        config_id=str(uuid.uuid4()),
    )
    return TestClient(app)


# ---- helpers ----


def _make_xlsx_bytes() -> bytes:
    """Create a minimal .xlsx file in memory."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "data"
    ws.append(["col_a", "col_b"])
    ws.append([1, 2])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _upload_file(name: str, data: bytes) -> tuple[str, bytes, str]:
    return (name, data, XLSX_CONTENT_TYPE)


# ---- health ----


def test_health():
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---- steps ----


def test_steps_list(client: TestClient):
    r = client.get("/steps")
    assert r.status_code == 200
    body = r.json()
    assert "ops" in body
    assert isinstance(body["ops"], list)
    assert "add" in body["ops"]


def test_steps_get(client: TestClient):
    r = client.get("/steps/add")
    assert r.status_code == 200
    body = r.json()
    assert body["op_name"] == "add"
    assert "input_schema" in body
    req_names = [f["name"] for f in body["input_schema"] if f.get("required")]
    assert "x" in req_names
    assert "y" in req_names
    assert "output_schema" in body
    out_names = [f["name"] for f in body["output_schema"]]
    assert "sum" in out_names


def test_steps_get_unknown_returns_404(client: TestClient):
    r = client.get("/steps/nonexistent_op")
    assert r.status_code == 404


# ---- inspect ----


def test_inspect_upload(client: TestClient):
    xlsx = _make_xlsx_bytes()

    r = client.post(
        "/inspect",
        files={"file": _upload_file("fileA_sample.xlsx", xlsx)},
        data={"input_profile_name": "demo_excel_inspect"},
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert "run_id" in body
    assert body["profile"]["detected_kind"] == "fileA"
    assert body["profile"]["filename"] == "fileA_sample.xlsx"


def test_inspect_unknown_profile_returns_error(client: TestClient):
    xlsx = _make_xlsx_bytes()

    r = client.post(
        "/inspect",
        files={"file": _upload_file("fileA_sample.xlsx", xlsx)},
        data={"input_profile_name": "nonexistent"},
    )

    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "reason" in detail


def test_configs_inspectable_filter(client: TestClient):
    """inspectable=true filters input_profiles to those with inspect_step_name."""
    engine = get_engine()
    assert engine.config_store is not None
    engine.config_store.put_spec(
        InputProfile,
        "detail_region",
        {"kind_rules": [{"pattern": ".*", "kind": "detail"}], "column_hints": ["A", "B"]},
        config_id=str(uuid.uuid4()),
    )

    r_all = client.get("/configs", params={"config_type": "input_profile"})
    assert r_all.status_code == 200
    names_all = [c["config_name"] for c in r_all.json()["configs"]]
    assert "demo_excel_inspect" in names_all
    assert "detail_region" in names_all

    r_inspectable = client.get(
        "/configs", params={"config_type": "input_profile", "inspectable": "true"}
    )
    assert r_inspectable.status_code == 200
    names_inspectable = [c["config_name"] for c in r_inspectable.json()["configs"]]
    assert "demo_excel_inspect" in names_inspectable
    assert "detail_region" not in names_inspectable


def test_inspect_profile_without_inspect_step_name_returns_error(client: TestClient):
    """Profile without inspect_step_name must return 400 (no inference from date_rule)."""
    engine = get_engine()
    assert engine.config_store is not None
    engine.config_store.put_spec(
        InputProfile,
        "no_inspect_step",
        {"kind_rules": [{"pattern": r".*\.xlsx$", "kind": "fileA"}]},
        config_id=str(uuid.uuid4()),
    )

    xlsx = _make_xlsx_bytes()
    r = client.post(
        "/inspect",
        files={"file": _upload_file("fileA_sample.xlsx", xlsx)},
        data={"input_profile_name": "no_inspect_step"},
    )

    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "inspect_step_name" in str(detail)


# ---- import ----


def test_import_excel(client: TestClient):
    xlsx = _make_xlsx_bytes()

    r = client.post(
        "/import",
        files={"file": _upload_file("fileA_sample.xlsx", xlsx)},
        data={
            "plan_name": "import_excel",
            "inputs": json.dumps({"entity_key": "default"}),
        },
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "succeeded"
    assert "run_id" in body
    assert len(body["artifacts_written"]) > 0


def test_import_unknown_plan_returns_error(client: TestClient):
    xlsx = _make_xlsx_bytes()

    r = client.post(
        "/import",
        files={"file": _upload_file("fileA_sample.xlsx", xlsx)},
        data={"plan_name": "nonexistent"},
    )

    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "reason" in detail


# ---- export ----


def test_export_excel_with_bindings(client: TestClient):
    engine = get_engine()

    # Pre-populate a DataFrame artifact that the export plan will consume
    df = pd.DataFrame({"col_a": [1, 2], "col_b": [3, 4]})
    engine.store.put_df("artifact/test/df", df)

    r = client.post(
        "/export",
        json={
            "plan_name": "export_excel",
            "bindings": {
                "in_key": "artifact/test/df",
            },
        },
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "succeeded"
    assert "run_id" in body
    assert len(body["artifacts_written"]) > 0


# ---- artifacts ----


def test_artifacts_list(client: TestClient):
    engine = get_engine()
    engine.store.put("artifact/smoke/a", 1)

    r = client.get("/artifacts", params={"prefix": "artifact/smoke/"})

    assert r.status_code == 200
    body = r.json()
    assert "artifact/smoke/a" in body["keys"]


def test_artifacts_get(client: TestClient):
    engine = get_engine()
    engine.store.put("artifact/smoke/val", 42)

    r = client.get("/artifacts/artifact/smoke/val")

    assert r.status_code == 200
    body = r.json()
    assert body["key"] == "artifact/smoke/val"
    assert body["value"] == 42


def test_artifacts_get_not_found(client: TestClient):
    # Use valid key format (run_id/entity_key/path) for non-existent artifact
    r = client.get("/artifacts/run1/unit1/nonexistent_path")

    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "reason" in detail


def test_runs_list_empty_with_in_memory_store(client_in_memory: TestClient):
    """In-memory store returns empty list for runs."""
    r = client_in_memory.get("/runs")
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_results_list_empty_with_in_memory_store(client_in_memory: TestClient):
    """In-memory store returns empty list for results."""
    r = client_in_memory.get("/results")
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_results_get_404_with_in_memory_store(client_in_memory: TestClient):
    """In-memory store returns 404 for result get."""
    r = client_in_memory.get("/results/run1/entity1")
    assert r.status_code == 404


def test_latest_results_list_empty_with_in_memory_store(client_in_memory: TestClient):
    """In-memory store returns empty list for latest_results."""
    r = client_in_memory.get("/latest_results")
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_entities_list_empty_with_in_memory_store(client_in_memory: TestClient):
    """In-memory store returns empty list for entities."""
    r = client_in_memory.get("/entities")
    assert r.status_code == 200
    assert r.json()["entries"] == []


# ---- integration: same tests against Postgres ----

_DB_URL = os.environ.get("FLOWBOOK_DATABASE_URL")
_skip_no_db = pytest.mark.skipif(not _DB_URL, reason="FLOWBOOK_DATABASE_URL not set")


@_skip_no_db
@pytest.mark.integration
class TestApiWithPostgres:
    """Re-run key API tests with a real Postgres backend."""

    def test_inspect_upload(self, client: TestClient):
        test_inspect_upload(client)

    def test_import_excel(self, client: TestClient):
        test_import_excel(client)

    def test_export_excel_with_bindings(self, client: TestClient):
        test_export_excel_with_bindings(client)

    def test_artifacts_roundtrip(self, client: TestClient):
        test_artifacts_list(client)
        test_artifacts_get(client)
