from __future__ import annotations

from typing import Any

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("plan_from_two_numbers")
class PlanFromTwoNumbersOp(BaseOp):
    """Demo planner: produces plan with add step."""

    class Inputs(BaseInputs):
        pass

    class Outputs(BaseOutputs):
        plan: dict[str, Any]

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        self.Inputs.model_validate(inputs)
        plan_config = {
            "steps": [
                {
                    "name": "add",
                    "op": "add",
                    "inputs": {"x": "@x", "y": "@y"},
                }
            ]
        }
        return self.Outputs(plan=plan_config).model_dump(mode="python")


register = register_from_steps()
