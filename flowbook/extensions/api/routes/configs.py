"""
Routes: GET /configs, GET /configs/{config_type}/{config_name}, POST /configs,
        PUT /configs/{config_type}/{config_name}, activate, deactivate,
        GET /configs/referenced, POST /configs/ai-edit
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from flowbook.core.configs.introspect import get_config_type_schema
from flowbook.core.configs.spec_types import CONFIG_TYPE_TO_SPEC_TYPE, Plan
from flowbook.core.logging import get_logger
from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import (
    ConfigAiEditRequest,
    ConfigCreateRequest,
    ConfigEntry,
    ConfigGetResponse,
    ConfigsListResponse,
    ConfigUpdateRequest,
    RunResponse,
)

router = APIRouter(prefix="/configs", tags=["configs"])
logger = get_logger(__name__)


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


def _parse_inputs_json(inputs_str: str) -> dict:
    """Parse inputs JSON. Returns {} on empty or invalid."""
    if not inputs_str or not inputs_str.strip():
        return {}
    try:
        parsed = json.loads(inputs_str)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _get_plan_input_schema(plan_name: str) -> list[dict[str, Any]]:
    """Return input keys for a plan: [{name, config_type}]. config_type=None for non-config."""
    store = _config_store()
    engine = get_engine()
    try:
        spec = store.get_spec(Plan, plan_name)
    except KeyError:
        return []
    plan_obj = spec.get("plan")
    if not isinstance(plan_obj, dict):
        return []
    steps = plan_obj.get("steps") or []
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for step_cfg in steps:
        if not isinstance(step_cfg, dict):
            continue
        op = step_cfg.get("op")
        step_inputs = step_cfg.get("inputs")
        if not op or not isinstance(step_inputs, dict):
            continue
        try:
            op_spec = engine.registry.get_op_spec(op)
        except Exception:
            continue
        for input_key, config_type in op_spec.config_refs.items():
            raw = step_inputs.get(input_key)
            if raw is None:
                continue
            logical = raw[1:] if isinstance(raw, str) and raw.startswith("@") else input_key
            if logical in seen:
                continue
            seen.add(logical)
            result.append({"name": logical, "config_type": config_type})
    return result


@router.get("/plan-inputs", summary="Get plan input schema for form")
def get_plan_inputs(
    plan_name: str = Query(..., description="Plan name"),
) -> dict:
    """Return input keys for a plan. config_type set = dropdown from configs of that type."""
    schema = _get_plan_input_schema(plan_name)
    return {"plan_name": plan_name, "inputs": schema}


@router.get("/referenced", summary="List configs referenced by a plan")
def list_referenced_configs(
    plan_name: str = Query(..., description="Plan name"),
    inputs: str = Query("{}", description="JSON dict: region_profile_name, mapping_name, etc."),
) -> dict:
    """Return (config_type, config_name) pairs referenced by the plan's steps.
    Resolves @refs using inputs dict."""
    store = _config_store()
    engine = get_engine()
    inputs_dict = _parse_inputs_json(inputs)

    try:
        spec = store.get_spec(Plan, plan_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail={"reason": str(e)}) from e

    plan_obj = spec.get("plan")
    if not isinstance(plan_obj, dict):
        raise HTTPException(
            status_code=400,
            detail={"reason": f"plan '{plan_name}' missing or invalid 'plan' key"},
        )

    steps = plan_obj.get("steps") or []
    if not isinstance(steps, list):
        raise HTTPException(
            status_code=400,
            detail={"reason": f"plan '{plan_name}' steps must be a list"},
        )

    seen: set[tuple[str, str]] = set()
    refs_list: list[dict[str, str]] = []

    for step_cfg in steps:
        if not isinstance(step_cfg, dict):
            continue
        op = step_cfg.get("op")
        step_inputs = step_cfg.get("inputs")
        if not op or not isinstance(step_inputs, dict):
            continue

        try:
            op_spec = engine.registry.get_op_spec(op)
        except Exception:
            continue

        for input_key, config_type in op_spec.config_refs.items():
            raw = step_inputs.get(input_key)
            if raw is None:
                continue
            if isinstance(raw, str) and raw.startswith("@"):
                logical = raw[1:]
                config_name = inputs_dict.get(logical, raw)
            else:
                config_name = raw
            if not isinstance(config_name, str) or not config_name.strip():
                continue
            pair = (config_type, config_name.strip())
            if pair not in seen:
                seen.add(pair)
                refs_list.append({"config_type": config_type, "config_name": config_name.strip()})

    return {"referenced": refs_list}


def _run_info_to_response(info) -> RunResponse:
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
        warnings=list(info.warnings),
    )


@router.post("/ai-edit", response_model=RunResponse, summary="Edit config via AI")
def ai_edit_config(body: ConfigAiEditRequest) -> RunResponse:
    """Edit config via spec_text (full spec). AI interprets -> spec. Needs OPENAI_API_KEY."""
    spec_text = body.spec_text
    logger.info(
        "ai_edit request",
        extra={
            "config_type": body.config_type,
            "config_name": body.config_name,
            "spec_text_len": len(spec_text),
            "inputs_keys": list((body.inputs or {}).keys()),
        },
    )
    if not spec_text.strip():
        raise HTTPException(status_code=400, detail={"reason": "spec_text must be non-empty"})

    if body.config_type not in CONFIG_TYPE_TO_SPEC_TYPE:
        raise HTTPException(
            status_code=400,
            detail={
                "reason": f"unknown config_type '{body.config_type}'. "
                f"Known: {sorted(CONFIG_TYPE_TO_SPEC_TYPE.keys())}"
            },
        )

    inputs = body.inputs or {}
    entity_key = inputs.get("entity_key", "default")
    if not isinstance(entity_key, str):
        entity_key = "default"

    engine = get_engine()
    try:
        with engine.create_run(entity_key=entity_key) as session:
            session.put_input("spec_text", spec_text)
            session.put_input("config_type", body.config_type)
            session.put_input("config_name", body.config_name)
            session.put_input("context", inputs)

            step_inputs: dict = {
                "spec_text": "@spec_text",
                "config_type": "@config_type",
                "config_name": "@config_name",
                "context": "@context",
            }

            plan_config = {
                "steps": [
                    {
                        "name": "ai_config",
                        "op": "ai_config",
                        "inputs": step_inputs,
                    }
                ]
            }
            info = session.exec_plan(plan_config=plan_config)
            logger.info(
                "ai_edit done",
                extra={
                    "run_id": info.run_id,
                    "status": info.status,
                    "config_type": body.config_type,
                    "config_name": body.config_name,
                    "errors": info.errors,
                },
            )
            return _run_info_to_response(info)
    except HTTPException:
        raise
    except Exception as e:
        raise to_http_error(e) from e


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
