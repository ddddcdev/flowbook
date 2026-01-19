"""
Registry:
- Resolve step names to callables/classes
Rule:
- Dependency resolution only
- No execution logic
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class UnknownOp(KeyError):
    """Raised when an operation name is not registered."""


OpFn = Callable[[dict[str, Any], Any], dict[str, Any]]
# 2nd arg is artifacts store (kept loose to avoid coupling)


@dataclass
class Registry:
    """
    Registry:
    - Resolve step names to callables/classes
    Rule:
    - Dependency resolution only
    - No execution logic
    """
    _ops: dict[str, OpFn] = field(default_factory=dict)

    def register(self, op: str, fn: OpFn) -> None:
        self._ops[op] = fn

    def get(self, op: str) -> OpFn:
        if op not in self._ops:
            raise UnknownOp(op)
        return self._ops[op]
