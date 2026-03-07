"""
Routes: GET /steps, GET /steps/{op_name}.

Minimal step introspection for plan composition (CLI, Streamlit, AI).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from flowbook.core.registry.registry import UnknownOp
from flowbook.extensions.api.deps import get_engine

router = APIRouter(prefix="/steps", tags=["steps"])


@router.get("/index")
def steps_index() -> dict:
    """Full index of all step specs (docstring, inputs, outputs, config_refs)."""
    engine = get_engine()
    ops = engine.registry.list_ops()
    specs = []
    for op_name in ops:
        spec = engine.registry.get_op_spec(op_name)
        specs.append(
            {
                "op_name": spec.op_name,
                "docstring": spec.docstring,
                "config_refs": spec.config_refs,
                "input_schema": spec.input_schema,
                "output_schema": spec.output_schema,
            }
        )
    return {"steps": specs}


@router.get("")
def list_steps() -> dict[str, list[str]]:
    """List all registered op names."""
    engine = get_engine()
    ops = engine.registry.list_ops()
    return {"ops": ops}


@router.get("/{op_name}")
def get_step(op_name: str) -> dict:
    """Get op spec: docstring, inputs (required/optional), outputs."""
    engine = get_engine()
    try:
        spec = engine.registry.get_op_spec(op_name)
    except UnknownOp as err:
        raise HTTPException(status_code=404, detail=f"Unknown op: {op_name}", headers=None) from err
    return {
        "op_name": spec.op_name,
        "docstring": spec.docstring,
        "config_refs": spec.config_refs,
        "input_schema": spec.input_schema,
        "output_schema": spec.output_schema,
    }
