"""
Routes: GET /entity_runs, GET /entity_runs/{run_id}/{entity_key},
        GET /latest_entity_runs, GET /latest_entity_runs/{entity_key}.

List and get entity_runs and latest_entity_runs. Postgres only.
In-memory store returns empty list / 404.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import (
    EntityRunEntry,
    EntityRunGetResponse,
    EntityRunsListResponse,
    LatestEntityRunGetResponse,
    LatestEntityRunsListResponse,
    ResultArtifactEntry,
)

router = APIRouter(tags=["entity_runs"])


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


def _dict_to_entry(d: dict) -> EntityRunEntry:
    return EntityRunEntry(
        run_id=d["run_id"],
        entity_key=d["entity_key"],
        status=d["status"],
        result_artifacts=_result_artifacts_to_entries(d.get("result_artifacts")),
        config_json=d.get("config_json"),
        created_at=d.get("created_at"),
        updated_at=d.get("updated_at"),
    )


def _store_supports_entity_runs(store: object) -> bool:
    return callable(getattr(store, "list_entity_runs", None))


@router.get("/entity_runs", response_model=EntityRunsListResponse, summary="List entity runs")
def list_entity_runs(
    run_id: str | None = None,
    entity_key: str | None = None,
) -> EntityRunsListResponse:
    """List entity_runs. run_id: within a run. entity_key: history for that entity."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_entity_runs(store):
        return EntityRunsListResponse(entries=[])
    try:
        # Duck typing: PostgresArtifactsStore has list_entity_runs
        rows = store.list_entity_runs(run_id=run_id, entity_key=entity_key)  # type: ignore[attr-defined]
        return EntityRunsListResponse(entries=[_dict_to_entry(r) for r in rows])
    except Exception as e:
        raise to_http_error(e) from e


@router.get(
    "/entity_runs/{run_id}/{entity_key:path}",
    response_model=EntityRunGetResponse,
    summary="Get entity run",
)
def get_entity_run(run_id: str, entity_key: str) -> EntityRunGetResponse:
    """Get single entity_run by (run_id, entity_key)."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_entity_runs(store):
        raise HTTPException(status_code=404, detail="entity_run not found")
    try:
        # Duck typing: PostgresArtifactsStore has get_entity_run
        row = store.get_entity_run(run_id=run_id, entity_key=entity_key)  # type: ignore[attr-defined]
        if row is None:
            raise HTTPException(status_code=404, detail="entity_run not found")
        return EntityRunGetResponse(
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
    "/latest_entity_runs",
    response_model=LatestEntityRunsListResponse,
    summary="List latest entity run per entity",
)
def list_latest_entity_runs(
    entity_key: str | None = None,
) -> LatestEntityRunsListResponse:
    """List latest entity_run per entity_key (updated_at max)."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_entity_runs(store):
        return LatestEntityRunsListResponse(entries=[])
    try:
        # Duck typing: PostgresArtifactsStore has list_latest_entity_runs
        rows = store.list_latest_entity_runs(entity_key=entity_key)  # type: ignore[attr-defined]
        return LatestEntityRunsListResponse(entries=[_dict_to_entry(r) for r in rows])
    except Exception as e:
        raise to_http_error(e) from e


@router.get(
    "/latest_entity_runs/{entity_key:path}",
    response_model=LatestEntityRunGetResponse,
    summary="Get latest entity run for entity",
)
def get_latest_entity_run(entity_key: str) -> LatestEntityRunGetResponse:
    """Get latest entity_run for entity_key (updated_at max)."""
    engine = get_engine()
    store = engine.store
    if not _store_supports_entity_runs(store):
        raise HTTPException(status_code=404, detail="latest_entity_run not found")
    try:
        # Duck typing: PostgresArtifactsStore has get_latest_entity_run
        row = store.get_latest_entity_run(entity_key=entity_key)  # type: ignore[attr-defined]
        if row is None:
            raise HTTPException(status_code=404, detail="latest_entity_run not found")
        return LatestEntityRunGetResponse(
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
