from __future__ import annotations

from typing import Any

from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.registry.spec import InputsBase, OutputsBase
from flowbook.runtime.store import RunStore


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


def register(registry: Registry) -> None:
    registry.register("plan_from_two_numbers", PlanFromTwoNumbersOp())
