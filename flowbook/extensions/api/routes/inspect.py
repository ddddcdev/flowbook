"""
Route: POST /inspect

Upload an Excel file (or filename only) -> run inspect plan -> return profile.
Profile's date_rule determines: with date_rule -> read bytes (inspect_excel_bytes_v2);
without -> filename only (inspect_filename).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from flowbook.core.configs.spec_types import InputProfile
from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import InspectResponse

router = APIRouter(tags=["inspect"])


@router.post("/inspect", response_model=InspectResponse)
async def inspect(
    file: Annotated[UploadFile | None, File()] = None,
    filename: Annotated[str | None, Form()] = None,
    entity_key: Annotated[str, Form()] = "default",
    input_profile_name: Annotated[str, Form()] = "demo_excel_inspect",
) -> InspectResponse:
    """
    Inspect an uploaded file or filename.

    - **file**: Optional. Excel (.xlsx, .xls) or CSV. Required when profile has date_rule.
    - **filename**: Required when file is omitted. Used for filename-only inspect.
    - **input_profile_name**: Config profile. date_rule -> file required; else filename-only.
    """
    engine = get_engine()
    config_store = engine.config_store
    if config_store is None:
        raise to_http_error(
            RuntimeError("Config store not configured; cannot resolve input profile")
        ) from None

    try:
        input_profile = config_store.get_spec(InputProfile, input_profile_name)
    except KeyError as e:
        raise to_http_error(ValueError(f"input_profile '{input_profile_name}' not found")) from e

    has_date_rule = bool(input_profile.get("date_rule"))
    contents: bytes = b""

    if has_date_rule:
        if file is None:
            raise to_http_error(
                ValueError("Profile has date_rule; file upload is required")
            ) from None
        contents = await file.read()
        fn = file.filename or "unknown.xlsx"
        if not (fn.lower().endswith(".xlsx") or fn.lower().endswith(".xls")):
            raise to_http_error(
                ValueError("Profile with date_rule requires Excel (.xlsx, .xls)")
            ) from None
    else:
        if file is not None:
            fn = file.filename or "unknown"
        elif filename:
            fn = filename.strip()
        else:
            raise to_http_error(
                ValueError("When file is omitted, filename (Form) is required")
            ) from None

    with engine.create_run(entity_key=entity_key) as session:
        try:
            session.put_input("input_profile_name", input_profile_name)
            session.put_input("src_excel_filename", fn)

            if has_date_rule:
                session.put_input_bytes("src_excel_bytes", contents)
                config = {
                    "name": "inspect",
                    "steps": [
                        {
                            "name": "inspect",
                            "op": "inspect_excel_bytes_v2",
                            "inputs": {
                                "input_profile_name": "@input_profile_name",
                                "src_excel_bytes": "@src_excel_bytes",
                                "src_excel_filename": "@src_excel_filename",
                            },
                        }
                    ],
                }
            else:
                session.put_input("filename", fn)
                config = {
                    "name": "inspect",
                    "steps": [
                        {
                            "name": "inspect",
                            "op": "inspect_filename",
                            "inputs": {
                                "input_profile_name": "@input_profile_name",
                                "filename": "@filename",
                            },
                        }
                    ],
                }

            info = session.exec_plan(plan_config=config)

            if info.status != "succeeded":
                raise ValueError(f"inspect failed (run_id={info.run_id}): {info.errors}")

            result_key = info.steps[0].outputs["result"]
            profile = session.get_dict(result_key)

            return InspectResponse(run_id=info.run_id, profile=profile)
        except Exception as e:
            raise to_http_error(e, run_id=session.run_id) from e
