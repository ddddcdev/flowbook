"""
Registry:
- Resolve step names to BaseOp instances. All ops are class-based.
- Spec is on the op; callers use op.Inputs for input contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from flowbook.core.registry.base_op import BaseOp


class UnknownOp(KeyError):
    """Raised when an operation name is not registered."""


def _format_annotation(ann: type) -> str:
    """Format type annotation for display."""
    origin = get_origin(ann)
    if origin is not None:
        args = get_args(ann)
        if origin is list:
            return f"list[{_format_annotation(args[0])}]" if args else "list"
        if origin is dict:
            return (
                f"dict[{_format_annotation(args[0])}, {_format_annotation(args[1])}]"
                if len(args) >= 2
                else "dict"
            )
        if origin is type(None) or (hasattr(origin, "__name__") and origin.__name__ == "NoneType"):
            return _format_annotation(args[0]) if args else "None"
        if hasattr(origin, "__name__") and origin.__name__ not in ("UnionType",):
            return f"{origin.__name__}[{', '.join(_format_annotation(a) for a in args)}]"
        # Union (e.g. int | float)
        if args:
            return " | ".join(_format_annotation(a) for a in args)
    if hasattr(ann, "__name__"):
        return ann.__name__
    return str(ann).replace("typing.", "")


def _model_to_fields(model: type[BaseModel]) -> list[dict[str, Any]]:
    """Extract field schema (name, type, required) from a Pydantic model."""
    schema = model.model_json_schema()
    required_set = set(schema.get("required", []))
    props = schema.get("properties", {})
    fields: list[dict[str, Any]] = []
    for name, info in props.items():
        # Prefer annotation from model_fields for accurate type string
        if hasattr(model, "model_fields") and name in model.model_fields:
            ann = model.model_fields[name].annotation
            type_str = _format_annotation(ann) if ann is not None else "any"
        else:
            type_str = info.get("type", "any")
            if isinstance(type_str, list):
                type_str = " | ".join(str(t) for t in type_str)
        fields.append(
            {
                "name": name,
                "type": type_str,
                "required": name in required_set,
            }
        )
    return fields


@dataclass
class OpSpec:
    """Introspection spec for a registered op. input_schema/output_schema are canonical."""

    op_name: str
    docstring: str | None
    config_refs: dict[str, str] = field(default_factory=dict)
    input_schema: list[dict[str, Any]] = field(default_factory=list)
    output_schema: list[dict[str, Any]] = field(default_factory=list)

    @property
    def required_inputs(self) -> tuple[str, ...]:
        return tuple(f["name"] for f in self.input_schema if f.get("required", False))

    @property
    def optional_inputs(self) -> tuple[str, ...]:
        return tuple(f["name"] for f in self.input_schema if not f.get("required", False))

    @property
    def output_keys(self) -> tuple[str, ...]:
        return tuple(f["name"] for f in self.output_schema)


@dataclass
class Registry:
    """Registry: name -> BaseOp instance."""

    _ops: dict[str, BaseOp] = field(default_factory=dict)

    def register(self, op_name: str, op_impl: BaseOp) -> None:
        self._ops[op_name] = op_impl

    def get(self, op_name: str) -> BaseOp:
        if op_name not in self._ops:
            raise UnknownOp(op_name)
        return self._ops[op_name]

    def list_ops(self) -> list[str]:
        """Return sorted list of registered op names."""
        return sorted(self._ops.keys())

    def get_op_spec(self, op_name: str) -> OpSpec:
        """Return introspection spec for the given op."""
        op = self.get(op_name)
        docstring = (op.__class__.__doc__ or "").strip() or None
        inp = op.Inputs
        config_refs = inp.config_refs()
        input_schema = _model_to_fields(inp)
        output_schema = _model_to_fields(op.Outputs)
        return OpSpec(
            op_name=op_name,
            docstring=docstring,
            config_refs=config_refs,
            input_schema=input_schema,
            output_schema=output_schema,
        )
