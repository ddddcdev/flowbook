"""
Base op: class-based operation with contract on the class.

- Subclass and set required_inputs, optional_inputs (use key constants to avoid duplication).
- Implement __call__(self, inputs, store) -> dict.
- Spec is owned by the op: callers use op.port_spec() when they need the contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from flowbook.registry.spec import PortSpec

if TYPE_CHECKING:
    from flowbook.runtime.store import RunStore


class BaseOp(ABC):
    """
    Base for all ops. Contract lives on the class; each op produces its PortSpec.

    Subclasses must set:
    - required_inputs: tuple of input param names (use module-level KEY_* constants).
    - optional_inputs: tuple of optional param names.
    If both are empty, the op has no input contract (any keys allowed; use for policy-only ops).

    Implement __call__(self, inputs, store) -> dict. The second argument is RunStore.
    """

    required_inputs: tuple[str, ...] = ()
    optional_inputs: tuple[str, ...] = ()

    def port_spec(self) -> PortSpec:
        """Return this op's input contract. Callers use this for preflight validation."""
        return PortSpec(required=self.required_inputs, optional=self.optional_inputs)

    @abstractmethod
    def __call__(self, inputs: dict[str, Any], store: "RunStore") -> dict[str, Any]:  # noqa: UP037
        """Execute the op. inputs are resolved values; store is the run-scoped RunStore."""
        ...
