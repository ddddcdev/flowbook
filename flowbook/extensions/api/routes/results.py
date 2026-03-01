"""
Routes: GET /results, GET /results/{run_id}/{entity_key},
        GET /latest_results, GET /latest_results/{entity_key}.

List and get results and latest_results. Postgres only.
In-memory store returns empty list / 404.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import (
    LatestResultGetResponse,
    LatestResultsListResponse,
    ResultArtifactEntry,
    ResultEntry,
    ResultGetResponse,
    ResultsListResponse,
)

router = APIRouter(tags=["results"])


def _result_artifacts_to_entries(
    ra: list[dict[str, Any]] | str | None,
) -> list[ResultArtifactEntry] | None:
    """Normalize result_artifacts to list. Handles scalar (legacy path string) as [path]."""
    if ra is None:
        return None
    if isinstance(ra, str) and ra.strip():
        return [ResultArtifactEntry(path=ra.strip(), label=None)]
    if not isinstance(ra, list):
        return None
    entries = [
        ResultArtifactEntry(path=item.get("path", ""), label=item.get("label"))
        for item in ra
        if isinstance(item, dict) and item.get("path")
    ]
    return entries if entries else None


def _dict_to_entry(d: dict) -> ResultEntry:
    return ResultEntry(
        run_id=d["run_id"],
        entity_key=d["entity_key"],
        status=d["status"],
        result_artifacts=_result_artifacts_to_entries(d.get("result_artifacts")),
        config_json=d.get("config_json"),
        created_at=d.get("created_at"),
        updated_at=d.get("updated_at"),
    )


def _store_supports_results(store: object) -> bool:
    return callable(getattr(store, "list_results", None))


@router.get("/results", response_model=ResultsListResponse, summary="List results")
def list_results(
    run_id: str | None = None,
    entity_key: str | None = None,
) -> ResultsListResponse:
    """List results. run_id: within a run. entity_key: history for that entity."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_results(store):
        return ResultsListResponse(entries=[])
    try:
        rows = store.list_results(run_id=run_id, entity_key=entity_key)  # type: ignore[attr-defined]
        return ResultsListResponse(entries=[_dict_to_entry(r) for r in rows])
    except Exception as e:
        raise to_http_error(e) from e


@router.get(
    "/results/{run_id}/{entity_key:path}",
    response_model=ResultGetResponse,
    summary="Get result",
)
def get_result(run_id: str, entity_key: str) -> ResultGetResponse:
    """Get single result by (run_id, entity_key)."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_results(store):
        raise HTTPException(status_code=404, detail="result not found")
    try:
        row = store.get_result(run_id=run_id, entity_key=entity_key)  # type: ignore[attr-defined]
        if row is None:
            raise HTTPException(status_code=404, detail="result not found")
        return ResultGetResponse(
            run_id=row["run_id"],
            entity_key=row["entity_key"],
            status=row["status"],
            result_artifacts=_result_artifacts_to_entries(row.get("result_artifacts")),
            config_json=row.get("config_json"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise to_http_error(e) from e


@router.get(
    "/latest_results",
    response_model=LatestResultsListResponse,
    summary="List latest result per entity",
)
def list_latest_results(
    entity_key: str | None = None,
) -> LatestResultsListResponse:
    """List latest result per entity_key (updated_at max)."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_results(store):
        return LatestResultsListResponse(entries=[])
    try:
        rows = store.list_latest_results(entity_key=entity_key)  # type: ignore[attr-defined]
        return LatestResultsListResponse(entries=[_dict_to_entry(r) for r in rows])
    except Exception as e:
        raise to_http_error(e) from e


@router.get(
    "/latest_results/{entity_key:path}",
    response_model=LatestResultGetResponse,
    summary="Get latest result for entity",
)
def get_latest_result(entity_key: str) -> LatestResultGetResponse:
    """Get latest result for entity_key (updated_at max)."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_results(store):
        raise HTTPException(status_code=404, detail="latest result not found")
    try:
        row = store.get_latest_result(entity_key=entity_key)  # type: ignore[attr-defined]
        if row is None:
            raise HTTPException(status_code=404, detail="latest result not found")
        return LatestResultGetResponse(
            run_id=row["run_id"],
            entity_key=row["entity_key"],
            status=row["status"],
            result_artifacts=_result_artifacts_to_entries(row.get("result_artifacts")),
            config_json=row.get("config_json"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise to_http_error(e) from e
