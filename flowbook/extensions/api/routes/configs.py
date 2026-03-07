"""
Routes: GET /configs, GET /configs/{kind}/{name}, POST /configs, PUT /configs/{kind}/{name},
        POST /configs/{kind}/{name}/activate, POST /configs/{kind}/{name}/deactivate
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from flowbook.core.configs.introspect import get_config_kind_schema
from flowbook.core.configs.spec_types import KIND_TO_SPEC_TYPE
from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import (
    ConfigCreateRequest,
    ConfigEntry,
    ConfigGetResponse,
    ConfigsListResponse,
    ConfigUpdateRequest,
)

router = APIRouter(prefix="/configs", tags=["configs"])


@router.get("/index")
def configs_index() -> dict:
    """Index of config kinds and config entries."""
    kinds = sorted(KIND_TO_SPEC_TYPE.keys())
    store = _config_store()
    try:
        if hasattr(store, "engine") and getattr(store, "engine", None) is not None:
            engine = store.engine  # type: ignore[reportAttributeAccessIssue]
            with engine.begin() as conn:
                rows = conn.execute(
                    text(
                        "SELECT kind, name FROM configs WHERE is_active = true ORDER BY kind, name"
                    )
                ).fetchall()
            configs = [{"kind": r[0], "name": r[1]} for r in rows]
        else:
            pairs = list(getattr(store, "_specs", {}).keys())
            configs = [{"kind": k, "name": n} for k, n in sorted(pairs)]
    except Exception as e:
        raise to_http_error(e) from e
    return {"kinds": kinds, "configs": configs}


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


@router.get("/schema/{kind}", summary="Get config kind schema")
def get_config_schema(kind: str) -> dict:
    """Return schema info for a config kind: docstring and field definitions."""
    try:
        return get_config_kind_schema(kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"reason": str(e)}) from e


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


def _spec_type_for_kind(kind: str):
    """Resolve spec_type from kind. Raises HTTPException 400 if unknown."""
    try:
        return KIND_TO_SPEC_TYPE[kind]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail={"reason": f"unknown kind '{kind}'. Known: {sorted(KIND_TO_SPEC_TYPE.keys())}"},
        ) from None


@router.post("", status_code=201, summary="Create config")
def create_config(body: ConfigCreateRequest) -> ConfigGetResponse:
    """Create a config. config_id is generated server-side."""
    store = _config_store()
    try:
        spec_type = _spec_type_for_kind(body.kind)
        config_id = str(uuid.uuid4())
        store.put_spec(spec_type, body.name, body.spec, config_id=config_id)
        spec = store._get_spec_by_kind(body.kind, body.name)
        return ConfigGetResponse(kind=body.kind, name=body.name, spec=spec)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"reason": str(e)}) from e
    except Exception as e:
        raise to_http_error(e) from e


@router.put("/{kind}/{name}", response_model=ConfigGetResponse, summary="Update config (upsert)")
def update_config(kind: str, name: str, body: ConfigUpdateRequest) -> ConfigGetResponse:
    """Upsert config spec. Creates if not exists."""
    store = _config_store()
    try:
        spec_type = _spec_type_for_kind(kind)
        config_id = str(uuid.uuid4())
        store.put_spec(spec_type, name, body.spec, config_id=config_id)
        spec = store._get_spec_by_kind(kind, name)
        return ConfigGetResponse(kind=kind, name=name, spec=spec)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"reason": str(e)}) from e
    except Exception as e:
        raise to_http_error(e) from e


@router.post("/{kind}/{name}/activate", status_code=204, summary="Activate config")
def activate_config(kind: str, name: str) -> None:
    """Set is_active=true. Postgres only."""
    store = _config_store()
    if not hasattr(store, "engine") or getattr(store, "engine", None) is None:
        raise HTTPException(
            status_code=501,
            detail={"reason": "activate/deactivate requires Postgres config store"},
        )
    with store.engine.begin() as conn:  # type: ignore[union-attr]
        r = conn.execute(
            text(
                "UPDATE configs SET is_active = true, updated_at = now() "
                "WHERE kind = :kind AND name = :name"
            ),
            {"kind": kind, "name": name},
        )
        if r.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail={"reason": f"config not found: kind={kind} name={name}"},
            )


@router.post("/{kind}/{name}/deactivate", status_code=204, summary="Deactivate config")
def deactivate_config(kind: str, name: str) -> None:
    """Set is_active=false. Postgres only. Deactivated configs are excluded from list/get."""
    store = _config_store()
    if not hasattr(store, "engine") or getattr(store, "engine", None) is None:
        raise HTTPException(
            status_code=501,
            detail={"reason": "activate/deactivate requires Postgres config store"},
        )
    with store.engine.begin() as conn:  # type: ignore[union-attr]
        r = conn.execute(
            text(
                "UPDATE configs SET is_active = false, updated_at = now() "
                "WHERE kind = :kind AND name = :name"
            ),
            {"kind": kind, "name": name},
        )
        if r.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail={"reason": f"config not found: kind={kind} name={name}"},
            )
