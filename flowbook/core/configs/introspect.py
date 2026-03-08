"""
Introspect ConfigSpecKind Spec types for schema documentation.

Returns config_type-level docstring and field info (name, type, required) for API/docs.
Expands nested TypedDicts (KindRule, DateRule, ResultArtifactSpec) for AI/config generation.
"""

from __future__ import annotations

import re
from typing import Any, NotRequired, get_args, get_origin

from flowbook.core.configs.spec_types import (
    CONFIG_TYPE_TO_SPEC_TYPE,
    DateRule,
    KindRule,
    ResultArtifactSpec,
)


def _format_annotation(ann: type) -> str:
    """Format annotation for display (simplified)."""
    origin = get_origin(ann)
    if origin is not None:
        args = get_args(ann)
        if origin is NotRequired:
            return _format_annotation(args[0]) if args else "any"
        if origin is list:
            return f"list[{_format_annotation(args[0])}]" if args else "list"
        if origin is dict:
            return (
                f"dict[{_format_annotation(args[0])}, {_format_annotation(args[1])}]"
                if len(args) >= 2
                else "dict"
            )
        if hasattr(origin, "__name__") and origin.__name__ not in ("NotRequired",):
            return f"{origin.__name__}[{', '.join(_format_annotation(a) for a in args)}]"
    if hasattr(ann, "__name__"):
        return ann.__name__
    s = str(ann)
    if "ForwardRef" in s:
        m = re.search(r"'([^']+)'", s)
        return m.group(1) if m else s
    return s


def _typeddict_to_fields(td: type) -> list[dict[str, Any]]:
    """Extract fields from a TypedDict for nested schema."""
    fields: list[dict[str, Any]] = []
    if not hasattr(td, "__annotations__"):
        return fields
    required_keys = getattr(td, "__required_keys__", frozenset())
    for name, ann in td.__annotations__.items():
        origin = get_origin(ann)
        is_not_required = origin is NotRequired or (
            hasattr(ann, "__forward_arg__") and "NotRequired" in str(ann)
        )
        required = not is_not_required and name in required_keys
        type_str = _format_annotation(ann)
        fields.append({"name": name, "type": type_str, "required": required})
    return fields


_NESTED_SCHEMAS: dict[type, list[dict[str, Any]]] = {
    KindRule: _typeddict_to_fields(KindRule),
    DateRule: _typeddict_to_fields(DateRule),
    ResultArtifactSpec: _typeddict_to_fields(ResultArtifactSpec),
}
_NESTED_BY_NAME: dict[str, list[dict[str, Any]]] = {
    "KindRule": _NESTED_SCHEMAS[KindRule],
    "DateRule": _NESTED_SCHEMAS[DateRule],
    "ResultArtifactSpec": _NESTED_SCHEMAS[ResultArtifactSpec],
}


def get_config_type_schema(config_type: str) -> dict[str, Any]:
    """Return schema info for a config type: docstring and field definitions."""
    try:
        spec_type = CONFIG_TYPE_TO_SPEC_TYPE[config_type]
    except KeyError as e:
        raise ValueError(
            f"unknown config_type '{config_type}'. Known: {sorted(CONFIG_TYPE_TO_SPEC_TYPE.keys())}"
        ) from e

    spec_cls = spec_type.Spec
    doc = (spec_cls.__doc__ or "").strip() or None

    fields: list[dict[str, Any]] = []
    if hasattr(spec_cls, "__annotations__"):
        for name, ann in spec_cls.__annotations__.items():
            origin = get_origin(ann)
            is_not_required = origin is NotRequired or (
                hasattr(ann, "__forward_arg__") and "NotRequired" in str(ann)
            )
            required = not is_not_required and name in getattr(
                spec_cls, "__required_keys__", frozenset()
            )
            type_str = _format_annotation(ann)
            field_entry: dict[str, Any] = {"name": name, "type": type_str, "required": required}
            # Expand nested TypedDict (e.g. list[KindRule] -> item_schema)
            args = get_args(ann) if origin is not None else ()
            if origin is list and args:
                item_cls = args[0]
                if item_cls in _NESTED_SCHEMAS:
                    field_entry["item_schema"] = _NESTED_SCHEMAS[item_cls]
            elif "KindRule" in type_str:
                field_entry["item_schema"] = _NESTED_BY_NAME["KindRule"]
            elif "DateRule" in type_str:
                field_entry["item_schema"] = _NESTED_BY_NAME["DateRule"]
            elif "ResultArtifactSpec" in type_str:
                field_entry["item_schema"] = _NESTED_BY_NAME["ResultArtifactSpec"]
            fields.append(field_entry)

    result: dict[str, Any] = {
        "config_type": config_type,
        "doc": doc,
        "fields": fields,
        "nested_types": {
            "KindRule": _NESTED_BY_NAME["KindRule"],
            "DateRule": _NESTED_BY_NAME["DateRule"],
            "ResultArtifactSpec": _NESTED_BY_NAME["ResultArtifactSpec"],
        },
    }

    # Plan: add nested plan structure (plan.plan dict shape)
    if config_type == "plan":
        result["plan_structure"] = {
            "doc": "Nested plan dict. Required: name, steps.",
            "fields": [
                {"name": "name", "type": "str", "required": True, "doc": "Plan name"},
                {
                    "name": "steps",
                    "type": "list[StepConfig]",
                    "required": True,
                    "doc": "Step sequence",
                    "item_schema": [
                        {"name": "name", "type": "str", "required": True, "doc": "Step name"},
                        {"name": "op", "type": "str", "required": True, "doc": "Op (steps index)"},
                        {
                            "name": "inputs",
                            "type": "dict",
                            "required": False,
                            "doc": "@ref or literal",
                        },
                    ],
                },
                {
                    "name": "result_artifacts",
                    "type": "list[ResultArtifactSpec]",
                    "required": False,
                    "doc": "Main result paths. Optional.",
                    "item_schema": _NESTED_SCHEMAS[ResultArtifactSpec],
                },
            ],
        }

    return result
