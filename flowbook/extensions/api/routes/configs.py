"""
Routes: GET /configs, GET /configs/{config_type}/{config_name}, POST /configs,
        PUT /configs/{config_type}/{config_name}, activate, deactivate
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from flowbook.core.configs.introspect import get_config_type_schema
from flowbook.core.configs.spec_types import CONFIG_TYPE_TO_SPEC_TYPE
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
    """Index of config types and config entries."""
    config_types = sorted(CONFIG_TYPE_TO_SPEC_TYPE.keys())
    store = _config_store()
    try:
        if hasattr(store, "engine") and getattr(store, "engine", None) is not None:
            engine = store.engine  # type: ignore[reportAttributeAccessIssue]
            with engine.begin() as conn:
                rows = conn.execute(
                    text(
                        "SELECT config_type, config_name FROM configs "
                        "WHERE is_active = true ORDER BY config_type, config_name"
                    )
                ).fetchall()
            configs = [{"config_type": r[0], "config_name": r[1]} for r in rows]
        else:
            pairs = list(getattr(store, "_specs", {}).keys())
            configs = [{"config_type": k, "config_name": n} for k, n in sorted(pairs)]
    except Exception as e:
        raise to_http_error(e) from e
    return {"config_types": config_types, "configs": configs}


def _config_store():
    engine = get_engine()
    if engine.config_store is None:
        raise RuntimeError("Config store not configured")
    return engine.config_store


@router.get("", response_model=ConfigsListResponse, summary="List configs")
def list_configs(
    config_type: str | None = Query(None, description="Filter by config type (e.g. input_profile)"),
    inspectable: bool = Query(
        False,
        description="When config_type=input_profile: return only profiles with inspect_step_name",
    ),
) -> ConfigsListResponse:
    """List config (config_type, config_name) entries. Optional config_type filter.
    inspectable=true filters input_profiles to those with inspect_step_name."""
    store = _config_store()
    try:
        if hasattr(store, "engine") and getattr(store, "engine", None) is not None:
            engine = store.engine  # type: ignore[reportAttributeAccessIssue]
            with engine.begin() as conn:
                if config_type:
                    if config_type == "input_profile" and inspectable:
                        rows = conn.execute(
                            text(
                                "SELECT config_type, config_name FROM configs "
                                "WHERE is_active = true AND config_type = :ct "
                                "AND spec->>'inspect_step_name' IS NOT NULL "
                                "AND spec->>'inspect_step_name' != '' "
                                "ORDER BY config_type, config_name"
                            ),
                            {"ct": config_type},
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            text(
                                "SELECT config_type, config_name FROM configs "
                                "WHERE is_active = true AND config_type = :ct "
                                "ORDER BY config_type, config_name"
                            ),
                            {"ct": config_type},
                        ).fetchall()
                else:
                    rows = conn.execute(
                        text(
                            "SELECT config_type, config_name FROM configs "
                            "WHERE is_active = true ORDER BY config_type, config_name"
                        )
                    ).fetchall()
            pairs = [(r[0], r[1]) for r in rows]
        else:
            # InMemoryConfigStore
            pairs = list(getattr(store, "_specs", {}).keys())
            if config_type:
                pairs = [(k, n) for k, n in pairs if k == config_type]
            if config_type == "input_profile" and inspectable:
                pairs = [
                    (k, n)
                    for k, n in pairs
                    if store._get_spec_by_config_type(k, n).get("inspect_step_name")
                ]
            pairs.sort()
        return ConfigsListResponse(
            configs=[ConfigEntry(config_type=k, config_name=n) for k, n in pairs]
        )
    except Exception as e:
        raise to_http_error(e) from e


@router.get("/schema/{config_type}", summary="Get config type schema")
def get_config_schema(config_type: str) -> dict:
    """Return schema info for a config type: docstring and field definitions."""
    try:
        return get_config_type_schema(config_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"reason": str(e)}) from e


@router.get(
    "/{config_type}/{config_name}",
    response_model=ConfigGetResponse,
    summary="Get config spec",
)
def get_config(config_type: str, config_name: str) -> ConfigGetResponse:
    """Return the spec dict for the given config_type and config_name."""
    store = _config_store()
    try:
        doc = store.get_config_document(config_type, config_name)
    except KeyError as e:
        if "config not found" in str(e):
            raise HTTPException(status_code=404, detail={"reason": str(e)}) from e
        raise to_http_error(e) from e
    return ConfigGetResponse(
        config_type=config_type,
        config_name=config_name,
        spec=doc["spec"],
        spec_text=doc.get("spec_text") or None,
    )


def _spec_type_for_config_type(config_type: str):
    """Resolve spec_type from config_type. Raises HTTPException 400 if unknown."""
    try:
        return CONFIG_TYPE_TO_SPEC_TYPE[config_type]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail={
                "reason": f"unknown config_type '{config_type}'. "
                f"Known: {sorted(CONFIG_TYPE_TO_SPEC_TYPE.keys())}"
            },
        ) from None


@router.post("", status_code=201, summary="Create config")
def create_config(body: ConfigCreateRequest) -> ConfigGetResponse:
    """Create a config. config_id is generated server-side."""
    store = _config_store()
    try:
        spec_type = _spec_type_for_config_type(body.config_type)
        config_id = str(uuid.uuid4())
        store.put_spec(
            spec_type,
            body.config_name,
            body.spec,
            config_id=config_id,
            spec_text=body.spec_text or "",
        )
        doc = store.get_config_document(body.config_type, body.config_name)
        return ConfigGetResponse(
            config_type=body.config_type,
            config_name=body.config_name,
            spec=doc["spec"],
            spec_text=doc.get("spec_text") or None,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"reason": str(e)}) from e
    except Exception as e:
        raise to_http_error(e) from e


@router.put(
    "/{config_type}/{config_name}",
    response_model=ConfigGetResponse,
    summary="Update config (upsert)",
)
def update_config(
    config_type: str, config_name: str, body: ConfigUpdateRequest
) -> ConfigGetResponse:
    """Upsert config spec. Creates if not exists."""
    store = _config_store()
    try:
        spec_type = _spec_type_for_config_type(config_type)
        config_id = str(uuid.uuid4())
        store.put_spec(
            spec_type,
            config_name,
            body.spec,
            config_id=config_id,
            spec_text=body.spec_text or "",
        )
        doc = store.get_config_document(config_type, config_name)
        return ConfigGetResponse(
            config_type=config_type,
            config_name=config_name,
            spec=doc["spec"],
            spec_text=doc.get("spec_text") or None,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"reason": str(e)}) from e
    except Exception as e:
        raise to_http_error(e) from e


@router.post(
    "/{config_type}/{config_name}/activate",
    status_code=204,
    summary="Activate config",
)
def activate_config(config_type: str, config_name: str) -> None:
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
                "WHERE config_type = :ct AND config_name = :cn"
            ),
            {"ct": config_type, "cn": config_name},
        )
        if r.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail={"reason": f"config not found: {config_type}/{config_name}"},
            )


@router.post(
    "/{config_type}/{config_name}/deactivate",
    status_code=204,
    summary="Deactivate config",
)
def deactivate_config(config_type: str, config_name: str) -> None:
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
                "WHERE config_type = :ct AND config_name = :cn"
            ),
            {"ct": config_type, "cn": config_name},
        )
        if r.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail={"reason": f"config not found: {config_type}/{config_name}"},
            )
