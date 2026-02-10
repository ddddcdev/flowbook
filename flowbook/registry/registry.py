"""
Registry:
- Resolve step names to callables/classes
- Optional PortSpec per op: required_inputs, optional_inputs (strict: no surplus)
Rule:
- Dependency resolution only
- No execution logic
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class UnknownOp(KeyError):
    """Raised when an operation name is not registered."""


OpFn = Callable[[dict[str, Any], Any], dict[str, Any]]
# 2nd arg is artifacts store (kept loose to avoid coupling)


@dataclass(frozen=True)
class PortSpec:
    """Minimal contract: allowed input param names. Strict: no surplus keys."""

    required: tuple[str, ...]
    optional: tuple[str, ...]

    def allowed_keys(self) -> frozenset[str]:
        return frozenset(self.required) | frozenset(self.optional)


@dataclass
class Registry:
    """
    Registry:
    - Resolve step names to callables/classes
    - Optional PortSpec per op for preflight validation
    """

    _ops: dict[str, OpFn] = field(default_factory=dict)
    _specs: dict[str, PortSpec] = field(default_factory=dict)

    def register(
        self,
        op: str,
        fn: OpFn,
        *,
        required_inputs: tuple[str, ...] = (),
        optional_inputs: tuple[str, ...] = (),
    ) -> None:
        self._ops[op] = fn
        if required_inputs or optional_inputs:
            self._specs[op] = PortSpec(required=required_inputs, optional=optional_inputs)

    def get(self, op: str) -> OpFn:
        if op not in self._ops:
            raise UnknownOp(op)
        return self._ops[op]

    def get_spec(self, op: str) -> PortSpec | None:
        return self._specs.get(op)
