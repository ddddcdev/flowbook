"""
Registry:
- Resolve step names to BaseOp instances. All ops are class-based.
- Spec is on the op; callers use op.Inputs for input contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from flowbook.registry.base_op import BaseOp


class UnknownOp(KeyError):
    """Raised when an operation name is not registered."""


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
