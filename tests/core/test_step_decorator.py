"""Tests for @step decorator and register_from_steps()."""

from __future__ import annotations

from typing import Any

from flowbook import Registry, register_from_steps, step
from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.runtime.store import RunStore


@step("doubler")
class DoublerOp(BaseOp):
    """Test op: doubles the input value."""

    class Inputs(BaseInputs):
        x: int | float

    class Outputs(BaseOutputs):
        out: int | float

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        return {"out": inputs["x"] * 2}


register = register_from_steps()


def test_step_decorator_registers_op() -> None:
    """register_from_steps() returns a function that registers @step-decorated classes."""
    registry = Registry()
    register(registry)
    op = registry.get("doubler")
    assert op is not None
    result = op({"x": 21}, None)  # type: ignore[arg-type]
    assert result["out"] == 42
