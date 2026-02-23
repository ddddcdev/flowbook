"""
Route: POST /import

Upload an Excel file + template_name -> run import plan -> artifacts.
"""

from __future__ import annotations

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


@router.post("/import", response_model=RunResponse)
async def import_file(
    file: Annotated[UploadFile, File(...)],
    template_name: Annotated[str, Form(...)],
    entity_key: Annotated[str, Form()] = "default",
    input_profile_name: Annotated[str, Form()] = "source",
    sheet_name: Annotated[str, Form()] = "data",
    header_row: Annotated[int, Form()] = 0,
    header_col: Annotated[int, Form()] = 0,
    region_profile_name: Annotated[str, Form()] = "detail_region",
    mapping_name: Annotated[str, Form()] = "detect_region_test",
) -> RunResponse:
    """
    Import an uploaded Excel file using a named plan template.

    - **file**: Excel file (.xlsx)
    - **template_name**: plan template (e.g. import_excel or import_excel_region)
    - **input_profile_name**: config profile for input handling
    - **sheet_name**: sheet to read (default: "data")
    - **header_row**: header row index, 0-based (default: 0)
    - **region_profile_name**: for import_excel_region template (default: "detail_region")
    """
    engine = get_engine()
    with engine.create_run(entity_key=entity_key) as session:
        try:
            contents = await file.read()

            # Store file bytes and register bindings
            session.put_input_bytes("src_excel_bytes", contents)
            session.put_input("input_profile_name", input_profile_name)
            session.put_input("template_name", template_name)

            # Defaults for read_excel_bytes template
            session.put_input("sheet_name", sheet_name)
            session.put_input("header_row", header_row)
            session.put_input("header_col", header_col)
            # For read_excel_detect_region template
            session.put_input("region_profile_name", region_profile_name)
            session.put_input("mapping_name", mapping_name)
            # Download filename for read/df: entity_key-based
            safe_key = entity_key.replace("/", "_").replace("\\", "_")
            session.put_input("import_output_filename", f"{safe_key}_imported.xlsx")

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

            planner_info, exec_info = session.exec_with_planner_once(planner_config=planner_config)

            return _run_info_to_response(exec_info)
        except Exception as e:
            raise to_http_error(e, run_id=session.run_id) from e
