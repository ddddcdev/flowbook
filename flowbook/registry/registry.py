"""
Registry:
- Resolve step names to BaseOp instances. All ops are class-based.
- Spec is on the op; callers use registry.get(op).port_spec() when needed.
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

    def register(self, op: str, fn: BaseOp) -> None:
        self._ops[op] = fn

    def get(self, op: str) -> BaseOp:
        if op not in self._ops:
            raise UnknownOp(op)
        return self._ops[op]
