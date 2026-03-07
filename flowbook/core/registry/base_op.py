"""
Base op: class-based operation. Contract lives on op.Inputs (Pydantic BaseModel).
Implement __call__(self, inputs, store) -> dict.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from flowbook.core.runtime.store import RunStore


class BaseInputs(BaseModel):
    """Base for op Inputs. Subclass and add fields. Use allowed_keys(), required_keys(), etc."""

    @classmethod
    def required_keys(cls) -> tuple[str, ...]:
        schema = cls.model_json_schema()
        return tuple(schema.get("required", []))

    @classmethod
    def optional_keys(cls) -> tuple[str, ...]:
        schema = cls.model_json_schema()
        required = set(schema.get("required", []))
        return tuple(k for k in schema.get("properties", {}).keys() if k not in required)

    @classmethod
    def allowed_keys(cls) -> frozenset[str]:
        return frozenset(cls.model_fields.keys())

    @classmethod
    def config_refs(cls) -> dict[str, str]:
        schema = cls.model_json_schema()
        refs: dict[str, str] = {}
        for name, prop in schema.get("properties", {}).items():
            kind = prop.get("x-config-kind")
            if isinstance(kind, str):
                refs[name] = kind
        return refs


class BaseOutputs(BaseModel):
    """Base for op Outputs. Subclass and add fields. Use allowed_keys()."""

    @classmethod
    def allowed_keys(cls) -> frozenset[str]:
        return frozenset(cls.model_fields.keys())


class BaseOp(ABC):
    """
    Base for all ops. Every op has Inputs and Outputs (Pydantic BaseModel).
    Subclasses override with inner class Inputs(BaseInputs) and class Outputs(BaseOutputs).
    Implement __call__(self, inputs, store) -> dict.

    Config refs: Field(json_schema_extra={"x-config-kind": "..."}) on Inputs.
    Subclass BaseInputs/BaseOutputs for allowed_keys(), required_keys(), etc.
    """

    Inputs: ClassVar[type[BaseInputs]] = BaseInputs
    Outputs: ClassVar[type[BaseOutputs]] = BaseOutputs

    @abstractmethod
    def __call__(self, inputs: dict[str, Any], store: "RunStore") -> dict[str, Any]:  # noqa: UP037
        """Execute the op. inputs are resolved values; store is the run-scoped RunStore."""
        ...
