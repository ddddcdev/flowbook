"""
Base op: class-based operation. Contract lives on op.Inputs (InputsBase).
Implement __call__(self, inputs, store) -> dict.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from flowbook.registry.spec import InputsBase, OutputsBase

if TYPE_CHECKING:
    from flowbook.runtime.store import RunStore


class _DefaultInputs(InputsBase):
    """Empty input contract. BaseOp uses this so every op has op.Inputs."""

    REQUIRED = ()
    OPTIONAL = ()


class _DefaultOutputs(OutputsBase):
    """Empty output contract. BaseOp uses this so every op has op.Outputs."""


class BaseOp(ABC):
    """
    Base for all ops. Every op has Inputs and Outputs; defaults are empty.
    Subclasses override with inner Inputs(InputsBase) and Outputs(OutputsBase).
    Implement __call__(self, inputs, store) -> dict.
    """

    Inputs: ClassVar[type[InputsBase]] = _DefaultInputs
    Outputs: ClassVar[type[OutputsBase]] = _DefaultOutputs

    @abstractmethod
    def __call__(self, inputs: dict[str, Any], store: "RunStore") -> dict[str, Any]:  # noqa: UP037
        """Execute the op. inputs are resolved values; store is the run-scoped RunStore."""
        ...
