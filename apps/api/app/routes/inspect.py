"""
Route: POST /inspect

Upload an Excel file → run inspect pipeline → return profile.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from apps.api.app.deps import get_engine
from apps.api.app.errors import to_http_error
from apps.api.app.schemas import InspectResponse

router = APIRouter(tags=["inspect"])


@router.post("/inspect", response_model=InspectResponse)
async def inspect(
    file: Annotated[UploadFile, File(...)],
    input_profile_name: Annotated[str, Form()] = "source",
) -> InspectResponse:
    """
    Inspect an uploaded Excel file.

    - **file**: Excel file (.xlsx)
    - **input_profile_name**: config profile to use for kind detection
    """
    engine = get_engine()
    session = engine.prepare()

    try:
        contents = await file.read()
        filename = file.filename or "unknown.xlsx"

        # Store bytes and register bindings
        session.put_input_bytes("src_excel_bytes", contents)
        session.put_input("src_excel_filename", filename)
        session.put_input("input_profile_name", input_profile_name)

        config = {
            "steps": [
                {
                    "name": "inspect",
                    "op": "inspect_excel_bytes_v2",
                    "inputs": {
                        "input_profile_name": "input_profile_name",
                        "src_excel_bytes": "src_excel_bytes",
                        "src_excel_filename": "src_excel_filename",
                    },
                }
            ]
        }

        info = session.exec(pipeline_config=config)

        if info.status != "succeeded":
            raise ValueError(f"inspect failed (run_id={info.run_id}): {info.errors}")

        result_key = info.steps[0].outputs["result"]
        profile = session.get_dict(result_key)

        return InspectResponse(run_id=info.run_id, profile=profile)

    except Exception as e:
        raise to_http_error(e, run_id=session.run_id) from e
