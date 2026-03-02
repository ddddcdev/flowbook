"""
Route: POST /import

Upload file (Excel or CSV) + template_name + inputs -> run import plan -> artifacts.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, UploadFile

from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import RunResponse

router = APIRouter(tags=["import"])


def _run_info_to_response(info: Any) -> RunResponse:
    return RunResponse(
        run_id=info.run_id,
        status=info.status,
        artifacts_written=list(info.artifacts_written),
        errors=list(info.errors),
        steps=[
            {
                "name": s.name,
                "status": s.status,
                "outputs": dict(s.outputs),
                "error": s.error,
            }
            for s in info.steps
        ],
    )


def _parse_inputs(inputs_str: str) -> dict[str, Any]:
    """Parse inputs JSON. Returns {} on empty or invalid."""
    if not inputs_str or not inputs_str.strip():
        return {}
    try:
        parsed = json.loads(inputs_str)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


@router.post("/import", response_model=RunResponse)
async def import_file(
    file: Annotated[UploadFile, File(...)],
    template_name: Annotated[str, Form(...)],
    inputs: Annotated[str, Form()] = "{}",
) -> RunResponse:
    """
    Import an uploaded file using a named plan template.

    - **file**: Excel (.xlsx, .xls) or CSV
    - **template_name**: plan template (e.g. import_excel_region, import_csv)
    - **inputs**: JSON with entity_key, encoding, sheet_name, target_month, etc.
    """
    engine = get_engine()
    inputs_dict = _parse_inputs(inputs)
    entity_key = inputs_dict.get("entity_key", "default")
    if not isinstance(entity_key, str):
        entity_key = "default"

    with engine.create_run(entity_key=entity_key) as session:
        try:
            contents = await file.read()
            filename = file.filename or ""

            # File type by extension
            ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
            if ext == "csv":
                session.put_input_bytes("src_csv_bytes", contents)
            elif ext in ("xlsx", "xls"):
                session.put_input_bytes("src_excel_bytes", contents)
                session.put_input("src_excel_filename", filename)
            else:
                raise ValueError(
                    f"Unsupported file extension '.{ext}'. Use .csv, .xlsx, or .xls"
                ) from None

            session.put_input("template_name", template_name)

            # Merge defaults for common template params
            defaults: dict[str, Any] = {
                "sheet_name": "data",
                "header_row": 0,
                "header_col": 0,
                "region_profile_name": "detail_region",
                "mapping_name": "detect_region_test",
            }
            merged = {**defaults, **inputs_dict}

            safe_key = entity_key.replace("/", "_").replace("\\", "_")
            merged["import_output_filename"] = f"{safe_key}_imported.xlsx"

            for k, v in merged.items():
                if k == "entity_key":
                    continue
                session.put_input(k, v)

            planner_config = {
                "name": "import",
                "steps": [
                    {
                        "name": "planner",
                        "op": "plan_from_template",
                        "inputs": {
                            "template_name": "@template_name",
                        },
                    }
                ],
            }

            planner_info, exec_info = session.exec_with_planner_once(
                planner_config=planner_config
            )

            return _run_info_to_response(exec_info)
        except Exception as e:
            raise to_http_error(e, run_id=session.run_id) from e
