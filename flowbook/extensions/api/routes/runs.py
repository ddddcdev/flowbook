"""
Routes: GET /runs, GET /runs/{run_id}.

List and get runs. Postgres only.
In-memory store returns empty list / 404.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import (
    RunEntry,
    RunGetResponse,
    RunsListResponse,
)

router = APIRouter(tags=["runs"])


def _store_supports_runs(store: object) -> bool:
    return callable(getattr(store, "list_runs", None))


@router.get("/runs", response_model=RunsListResponse, summary="List runs")
def list_runs(run_id: str | None = None) -> RunsListResponse:
    """List runs with optional run_id filter."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_runs(store):
        return RunsListResponse(entries=[])
    try:
        # Duck typing: PostgresArtifactsStore has list_runs
        rows = store.list_runs(run_id=run_id)  # type: ignore[attr-defined]
        return RunsListResponse(
            entries=[
                RunEntry(
                    run_id=r["run_id"],
                    status=r["status"],
                    config_json=r.get("config_json"),
                    created_at=r.get("created_at"),
                    updated_at=r.get("updated_at"),
                )
                for r in rows
            ]
        )
    except Exception as e:
        raise to_http_error(e) from e


@router.get(
    "/runs/{run_id}",
    response_model=RunGetResponse,
    summary="Get run",
)
def get_run(run_id: str) -> RunGetResponse:
    """Get single run by run_id."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_runs(store):
        raise HTTPException(status_code=404, detail="run not found")
    try:
        # Duck typing: PostgresArtifactsStore has get_run
        row = store.get_run(run_id=run_id)  # type: ignore[attr-defined]
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")
        return RunGetResponse(
            run_id=row["run_id"],
            status=row["status"],
            config_json=row.get("config_json"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise to_http_error(e) from e
