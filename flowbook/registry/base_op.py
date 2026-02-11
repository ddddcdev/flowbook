"""
Base op: class-based operation. Contract lives on op.Inputs (InputsBase).
Implement __call__(self, inputs, store) -> dict.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from flowbook.registry.spec import InputsBase

if TYPE_CHECKING:
    from flowbook.runtime.store import RunStore


class _DefaultInputs(InputsBase):
    """Empty input contract. BaseOp uses this so every op has op.Inputs."""

    REQUIRED = ()
    OPTIONAL = ()


class BaseOp(ABC):
    """
    Base for all ops. Every op has Inputs; default is empty (no preflight).
    Subclasses override Inputs with inner class Inputs(InputsBase) and REQUIRED/OPTIONAL.
    Implement __call__(self, inputs, store) -> dict.
    """

    Inputs: ClassVar[type[InputsBase]] = _DefaultInputs

    @abstractmethod
    def __call__(self, inputs: dict[str, Any], store: "RunStore") -> dict[str, Any]:  # noqa: UP037
        """Execute the op. inputs are resolved values; store is the run-scoped RunStore."""
        ...
