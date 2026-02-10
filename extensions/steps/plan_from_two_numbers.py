from __future__ import annotations

from flowbook.registry.base_op import BaseOp


class PlanFromTwoNumbersOp(BaseOp):
    """Planner: produces plan with add step. No inputs required for this policy."""
    required_inputs = ()
    optional_inputs = ()

    def __call__(self, inputs: dict, store_) -> dict:
        plan_config = {
            "steps": [
                {
                    "name": "add",
                    "op": "add",
                    "inputs": {"x": "x", "y": "y"},
                }
            ]
        }
        return {"plan": plan_config}


def register(registry) -> None:
    registry.register("plan_from_two_numbers", PlanFromTwoNumbersOp())
