"""
Smoke test for the FastAPI sample app.

Verifies:
- /health returns 200
- POST /inspect with an Excel file returns a profile
- POST /import with a file + template executes a plan
- POST /export with bindings executes an export plan
- GET /artifacts lists keys; GET /artifacts/{key} retrieves value
- Failure responses include run_id + reason
"""

from __future__ import annotations

import os
import uuid
from io import BytesIO

import openpyxl
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from flowbook.core.configs.spec_types import InputProfile, PlanTemplate
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


@pytest.fixture()
def client() -> TestClient:
    """Seed config store with test configs, then return a TestClient."""
    engine = get_engine()
    assert engine.config_store is not None

    # InputProfile for inspect
    engine.config_store.put_spec(
        InputProfile,
        "source",
        {
            "kind_rules": [
                {"pattern": r"^fileA_.*\.xlsx$", "kind": "fileA"},
            ]
        },
        config_id=str(uuid.uuid4()),
    )

    # PlanTemplate for import: read excel bytes → df artifact
    engine.config_store.put_spec(
        PlanTemplate,
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

    # PlanTemplate for export: write DataFrame to Excel bytes
    engine.config_store.put_spec(
        PlanTemplate,
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
    assert "required_inputs" in body
    assert "x" in body["required_inputs"]
    assert "y" in body["required_inputs"]
    assert "output_keys" in body
    assert "sum" in body["output_keys"]


def test_steps_get_unknown_returns_404(client: TestClient):
    r = client.get("/steps/nonexistent_op")
    assert r.status_code == 404


# ---- inspect ----


def test_inspect_upload(client: TestClient):
    xlsx = _make_xlsx_bytes()

    r = client.post(
        "/inspect",
        files={"file": _upload_file("fileA_sample.xlsx", xlsx)},
        data={"input_profile_name": "source"},
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
    assert detail["run_id"] is not None
    assert "reason" in detail


# ---- import ----


def test_import_excel(client: TestClient):
    xlsx = _make_xlsx_bytes()

    r = client.post(
        "/import",
        files={"file": _upload_file("fileA_sample.xlsx", xlsx)},
        data={
            "template_name": "import_excel",
            "input_profile_name": "source",
        },
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "succeeded"
    assert "run_id" in body
    assert len(body["artifacts_written"]) > 0


def test_import_unknown_template_returns_error(client: TestClient):
    xlsx = _make_xlsx_bytes()

    r = client.post(
        "/import",
        files={"file": _upload_file("fileA_sample.xlsx", xlsx)},
        data={"template_name": "nonexistent"},
    )

    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["run_id"] is not None
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
            "template_name": "export_excel",
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


def test_runs_list_empty_with_in_memory_store(client: TestClient):
    """In-memory store returns empty list for runs."""
    r = client.get("/runs")
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_results_list_empty_with_in_memory_store(client: TestClient):
    """In-memory store returns empty list for results."""
    r = client.get("/results")
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_results_get_404_with_in_memory_store(client: TestClient):
    """In-memory store returns 404 for result get."""
    r = client.get("/results/run1/entity1")
    assert r.status_code == 404


def test_latest_results_list_empty_with_in_memory_store(client: TestClient):
    """In-memory store returns empty list for latest_results."""
    r = client.get("/latest_results")
    assert r.status_code == 200
    assert r.json()["entries"] == []


def test_entities_list_empty_with_in_memory_store(client: TestClient):
    """In-memory store returns empty list for entities."""
    r = client.get("/entities")
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
