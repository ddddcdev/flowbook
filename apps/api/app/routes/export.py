"""
Route: POST /export

Execute an export pipeline on existing artifacts (no file upload).
Bindings map logical names to full artifact keys from previous runs;
bind() registers them directly (no data copy needed).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from apps.api.app.deps import get_engine
from apps.api.app.errors import to_http_error
from apps.api.app.schemas import ExportRequest, RunResponse

router = APIRouter(tags=["export"])


@router.post("/export", response_model=RunResponse)
def export_artifacts(req: ExportRequest) -> RunResponse:
    """
    Run an export pipeline over existing artifacts.

    - **template_name**: pipeline template to resolve from config store
    - **bindings**: map of logical name → full artifact key
    """
    engine = get_engine()
    session = engine.prepare()

    try:
        # Store artifact keys as JSON inputs so ops can dereference them
        # (same pattern as import's src_excel_bytes_key).
        for name, artifact_key in req.bindings.items():
            session.put_input(name, artifact_key)

        session.put_input("template_name", req.template_name)

        planner_config: dict[str, Any] = {
            "steps": [
                {
                    "name": "planner",
                    "op": "plan_from_template",
                    "inputs": {
                        "template_name": "template_name",
                    },
                }
            ]
        }

        planner_info, exec_info = session.exec_with_plan_once(
            planner_config=planner_config
        )

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
