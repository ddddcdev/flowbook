"""
Route: POST /export (JSON), POST /export (Form)

Execute an export plan on existing artifacts (no file upload).
- JSON: plan_name + bindings + inputs
- Form: source_artifact_key + plan_name + inputs (export_excel_region default)
"""

from __future__ import annotations

import json
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

    - **plan_name**: plan to resolve from config store
    - **bindings**: map of logical name -> full artifact key
    - **inputs**: optional key-value params for the plan
    """
    engine = get_engine()
    with engine.create_run() as session:
        try:
            for name, artifact_key in req.bindings.items():
                session.bind(name, artifact_key)

            session.put_input("plan_name", req.plan_name)
            for k, v in req.inputs.items():
                session.put_input(k, v)

            planner_config: dict[str, Any] = {
                "name": "export",
                "steps": [
                    {
                        "name": "planner",
                        "op": "load_plan",
                        "inputs": {
                            "plan_name": "@plan_name",
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


def _parse_export_inputs(inputs_str: str) -> dict[str, Any]:
    """Parse inputs JSON. Returns {} on empty or invalid."""
    if not inputs_str or not inputs_str.strip():
        return {}
    try:
        parsed = json.loads(inputs_str)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


@router.post(
    "/export/from_artifact",
    response_model=RunResponse,
    summary="Export from an import (filter/map + write)",
)
async def export_from_artifact(
    source_artifact_key: Annotated[str, Form(...)],
    entity_key: Annotated[str, Form()] = "default",
    mapping_name: Annotated[str, Form()] = "detect_region_test",
    plan_name: Annotated[str, Form()] = "export_excel_region",
    inputs: Annotated[str, Form()] = "{}",
) -> RunResponse:
    """
    Run export plan on an existing import: load DataFrame at source_artifact_key,
    apply mapping, write xlsx. plan_name and inputs allow extensibility.
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

    inputs_dict = _parse_export_inputs(inputs)
    entity_key = inputs_dict.get("entity_key", entity_key)
    if not isinstance(entity_key, str):
        entity_key = "default"

    with engine.create_run(entity_key=entity_key) as session:
        try:
            safe_key = entity_key.replace("/", "_").replace("\\", "_")
            base_inputs: dict[str, Any] = {
                "artifact_key": source_artifact_key,
                "mapping_name": mapping_name,
                "output_filename": f"{safe_key}_exported.xlsx",
            }
            merged = {**base_inputs, **inputs_dict}

            session.put_input("plan_name", plan_name)
            for k, v in merged.items():
                if k == "entity_key":
                    continue
                session.put_input(k, v)

            planner_config = {
                "name": "export",
                "steps": [
                    {
                        "name": "planner",
                        "op": "load_plan",
                        "inputs": {"plan_name": "@plan_name"},
                    }
                ],
            }
            planner_info, exec_info = session.exec_with_planner_once(planner_config=planner_config)
            return _run_info_to_response(exec_info)
        except Exception as e:
            raise to_http_error(e, run_id=session.run_id) from e
