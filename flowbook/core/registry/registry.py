"""
Registry:
- Resolve step names to BaseOp instances. All ops are class-based.
- Spec is on the op; callers use op.Inputs for input contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from flowbook.core.registry.base_op import BaseOp


class UnknownOp(KeyError):
    """Raised when an operation name is not registered."""


@dataclass
class OpSpec:
    """Introspection spec for a registered op."""

    op_name: str
    docstring: str | None
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    output_keys: tuple[str, ...]


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
        required = tuple(inp.REQUIRED) if inp.REQUIRED else ()
        optional = tuple(inp.OPTIONAL) if inp.OPTIONAL else ()
        out_keys = tuple(op.Outputs.allowed_keys())
        return OpSpec(
            op_name=op_name,
            docstring=docstring,
            required_inputs=required,
            optional_inputs=optional,
            output_keys=out_keys,
        )
