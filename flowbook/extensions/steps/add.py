from __future__ import annotations

from typing import Any

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("add")
class AddOp(BaseOp):
    class Inputs(InputsBase):
        X = "x"
        Y = "y"
        REQUIRED = (X, Y)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        SUM = "sum"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        return {self.Outputs.SUM: inputs[self.Inputs.X] + inputs[self.Inputs.Y]}


register = register_from_steps()
