"""
Route: POST /export (JSON), POST /export (Form)

Execute an export plan on existing artifacts (no file upload).
- JSON: template_name + bindings (logical name -> artifact key)
- Form: source_artifact_key + mapping_name (uses export_excel_region template)
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Form

from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import ExportRequest, RunResponse

router = APIRouter(tags=["export"])


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


@router.post("/export", response_model=RunResponse)
def export_artifacts(req: ExportRequest) -> RunResponse:
    """
    Run an export plan over existing artifacts.

    - **template_name**: plan template to resolve from config store
    - **bindings**: map of logical name -> full artifact key
    """
    engine = get_engine()
    session = engine.prepare()

    try:
        for name, artifact_key in req.bindings.items():
            session.bind(name, artifact_key)

        session.put_input("template_name", req.template_name)

        planner_config: dict[str, Any] = {
            "name": "export",
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

        return RunResponse(
            run_id=exec_info.run_id,
            status=exec_info.status,
            artifacts_written=list(exec_info.artifacts_written),
            errors=list(exec_info.errors),
            steps=[
                {
                    "name": s.name,
                    "status": s.status,
                    "outputs": dict(s.outputs),
                    "error": s.error,
                }
                for s in exec_info.steps
            ],
        )

    except Exception as e:
        raise to_http_error(e, run_id=session.run_id) from e


@router.post(
    "/export/from_artifact",
    response_model=RunResponse,
    summary="Export from an import (filter/map + write)",
)
async def export_from_artifact(
    source_artifact_key: Annotated[str, Form(...)],
    entity_key: Annotated[str, Form()] = "default",
    mapping_name: Annotated[str, Form()] = "detect_region_test",
) -> RunResponse:
    """
    Run export plan on an existing import: load DataFrame at source_artifact_key,
    apply mapping, write xlsx. Uses export_excel_region template.
    """
    engine = get_engine()
    try:
        val = engine.store.get_any(source_artifact_key)
    except Exception as e:
        raise to_http_error(e) from e

    if type(val).__name__ != "DataFrame":
        raise to_http_error(
            ValueError(
                f"Artifact {source_artifact_key!r} is not a DataFrame; use an import (read/df) key."
            )
        ) from None

    session = engine.prepare(entity_key=entity_key)
    try:
        session.put_input("template_name", "export_excel_region")
        session.put_input("artifact_key", source_artifact_key)
        session.put_input("mapping_name", mapping_name)
        # Download filename: entity_key-based
        safe_key = entity_key.replace("/", "_").replace("\\", "_")
        session.put_input("output_filename", f"{safe_key}_exported.xlsx")

        planner_config = {
            "name": "export",
            "steps": [
                {
                    "name": "planner",
                    "op": "plan_from_template",
                    "inputs": {"template_name": "@template_name"},
                }
            ],
        }
        planner_info, exec_info = session.exec_with_planner_once(planner_config=planner_config)
        return _run_info_to_response(exec_info)
    except Exception as e:
        raise to_http_error(e, run_id=session.run_id) from e
