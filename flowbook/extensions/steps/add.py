from __future__ import annotations

from typing import Any

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("add")
class AddOp(BaseOp):
    class Inputs(BaseInputs):
        x: int | float
        y: int | float

    class Outputs(BaseOutputs):
        sum: int | float

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        return self.Outputs(sum=inp.x + inp.y).model_dump(mode="python")


register = register_from_steps()
