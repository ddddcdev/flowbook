"""
Routes: GET /configs, GET /configs/{kind}/{name}

List and get config specs from the Postgres config store.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import text

from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import ConfigEntry, ConfigGetResponse, ConfigsListResponse

router = APIRouter(prefix="/configs", tags=["configs"])


def _config_store():
    engine = get_engine()
    if engine.config_store is None:
        raise RuntimeError("Config store not configured")
    return engine.config_store


@router.get("", response_model=ConfigsListResponse, summary="List configs")
def list_configs(
    kind: str | None = Query(None, description="Filter by config kind (e.g. input_profile)"),
    inspectable: bool = Query(
        False,
        description="When kind=input_profile: return only profiles with inspect_step_name",
    ),
) -> ConfigsListResponse:
    """List config (kind, name) entries. Optional kind filter.
    inspectable=true filters input_profiles to those with inspect_step_name."""
    store = _config_store()
    try:
        if hasattr(store, "engine") and getattr(store, "engine", None) is not None:
            engine = store.engine  # type: ignore[reportAttributeAccessIssue]
            with engine.begin() as conn:
                if kind:
                    if kind == "input_profile" and inspectable:
                        rows = conn.execute(
                            text(
                                "SELECT kind, name FROM configs "
                                "WHERE is_active = true AND kind = :kind "
                                "AND spec->>'inspect_step_name' IS NOT NULL "
                                "AND spec->>'inspect_step_name' != '' "
                                "ORDER BY kind, name"
                            ),
                            {"kind": kind},
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            text(
                                "SELECT kind, name FROM configs "
                                "WHERE is_active = true AND kind = :kind ORDER BY kind, name"
                            ),
                            {"kind": kind},
                        ).fetchall()
                else:
                    rows = conn.execute(
                        text(
                            "SELECT kind, name FROM configs "
                            "WHERE is_active = true ORDER BY kind, name"
                        )
                    ).fetchall()
            pairs = [(r[0], r[1]) for r in rows]
        else:
            # InMemoryConfigStore
            pairs = list(getattr(store, "_specs", {}).keys())
            if kind:
                pairs = [(k, n) for k, n in pairs if k == kind]
            if kind == "input_profile" and inspectable:
                pairs = [
                    (k, n)
                    for k, n in pairs
                    if store._get_spec_by_kind(k, n).get("inspect_step_name")
                ]
            pairs.sort()
        return ConfigsListResponse(configs=[ConfigEntry(kind=k, name=n) for k, n in pairs])
    except Exception as e:
        raise to_http_error(e) from e


@router.get(
    "/{kind}/{name}",
    response_model=ConfigGetResponse,
    summary="Get config spec",
)
def get_config(kind: str, name: str) -> ConfigGetResponse:
    """Return the spec dict for the given kind and name."""
    from fastapi import HTTPException

    store = _config_store()
    try:
        spec = store._get_spec_by_kind(kind, name)
    except KeyError as e:
        if "config not found" in str(e):
            raise HTTPException(status_code=404, detail={"reason": str(e)}) from e
        raise to_http_error(e) from e
    return ConfigGetResponse(kind=kind, name=name, spec=spec)
