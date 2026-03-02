"""
Route: GET /entities

List registered entities. Postgres only; in-memory store returns empty list.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter

from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import EntitiesListResponse, EntityEntry

router = APIRouter(tags=["entities"])


def _dict_to_entry(d: dict[str, Any]) -> EntityEntry:
    return EntityEntry(
        entity_key=d["entity_key"],
        meta=d.get("meta") or {},
        created_at=d.get("created_at"),
        updated_at=d.get("updated_at"),
    )


@router.get("/entities", response_model=EntitiesListResponse, summary="List entities")
def list_entities() -> EntitiesListResponse:
    """List all registered entities (entity_key, meta, created_at, updated_at)."""
    engine = get_engine()
    store = engine.store
    list_entities_fn = getattr(store, "list_entities", None)
    if not callable(list_entities_fn):
        return EntitiesListResponse(entries=[])
    try:
        rows = cast(list[dict], list_entities_fn())
        return EntitiesListResponse(entries=[_dict_to_entry(r) for r in rows])
    except Exception as e:
        raise to_http_error(e) from e
