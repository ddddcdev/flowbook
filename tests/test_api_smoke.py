"""
Smoke test for the FastAPI sample app.

Verifies:
- /health returns 200
- POST /inspect with an Excel file returns a profile
- POST /import with a file + template executes a pipeline
- POST /export with bindings executes an export pipeline
- GET /artifacts lists keys; GET /artifacts/{key} retrieves value
- Failure responses include run_id + reason
"""

from __future__ import annotations

from io import BytesIO

import openpyxl
import pytest
from fastapi.testclient import TestClient

from apps.api.app.deps import get_engine
from apps.api.app.main import app
from flowbook.configs.spec_types import InputProfile, PlanTemplate

pytestmark = pytest.mark.smoke

XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


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
        config_id="smoke-source",
    )

    # PlanTemplate for import: read excel bytes → df artifact
    engine.config_store.put_spec(
        PlanTemplate,
        "import_excel",
        {
            "plan": {
                "steps": [
                    {
                        "name": "read",
                        "op": "read_excel_bytes",
                        "inputs": {
                            "bytes_key": "src_excel_bytes_key",
                            "out_key": "out_key_read",
                            "sheet": "sheet_name",
                            "header": "header_row",
                        },
                    }
                ]
            }
        },
        config_id="smoke-import",
    )

    # PlanTemplate for export: add two numbers (simplest op for smoke test)
    engine.config_store.put_spec(
        PlanTemplate,
        "export_add",
        {
            "plan": {
                "steps": [
                    {
                        "name": "add",
                        "op": "add",
                        "inputs": {"x": "x", "y": "y"},
                    }
                ]
            }
        },
        config_id="smoke-export",
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


def test_export_with_bindings(client: TestClient):
    engine = get_engine()

    # Pre-populate artifacts that the export pipeline will consume
    engine.store.put("artifact:test/x", 10)
    engine.store.put("artifact:test/y", 20)

    r = client.post(
        "/export",
        json={
            "template_name": "export_add",
            "bindings": {
                "x": "artifact:test/x",
                "y": "artifact:test/y",
            },
        },
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "succeeded"
    assert "run_id" in body


# ---- artifacts ----


def test_artifacts_list(client: TestClient):
    engine = get_engine()
    engine.store.put("artifact:smoke/a", 1)

    r = client.get("/artifacts", params={"prefix": "artifact:smoke/"})

    assert r.status_code == 200
    body = r.json()
    assert "artifact:smoke/a" in body["keys"]


def test_artifacts_get(client: TestClient):
    engine = get_engine()
    engine.store.put("artifact:smoke/val", 42)

    r = client.get("/artifacts/artifact:smoke/val")

    assert r.status_code == 200
    body = r.json()
    assert body["key"] == "artifact:smoke/val"
    assert body["value"] == 42


def test_artifacts_get_not_found(client: TestClient):
    r = client.get("/artifacts/nonexistent_key")

    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "reason" in detail
