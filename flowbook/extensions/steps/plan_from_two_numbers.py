from __future__ import annotations

from typing import Any

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("plan_from_two_numbers")
class PlanFromTwoNumbersOp(BaseOp):
    """Planner: produces plan with add step. No inputs required for this policy."""

    class Inputs(InputsBase):
        REQUIRED = ()
        OPTIONAL = ()

    class Outputs(OutputsBase):
        PLAN = "plan"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        plan_config = {
            "steps": [
                {
                    "name": "add",
                    "op": "add",
                    "inputs": {"x": "x", "y": "y"},
                }
            ]
        }
        return {self.Outputs.PLAN: plan_config}


register = register_from_steps()
