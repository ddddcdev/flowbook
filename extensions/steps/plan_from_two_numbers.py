from __future__ import annotations


def plan_from_two_numbers_op(inputs: dict, store_):
    """
    Policy:
    - planner = policy decision (produces plan), not execution.
    - Planner may consume resolved values (e.g., Excel contents) for decision-making.
    - Produced plan MUST use logical names for inputs (no artifact keys).
      Artifact bindings are supplied externally via RunContext.bindings.
    - Returns plan as output value; runtime persists it and records key in StepRunInfo.outputs.
    """

    # inputs は値（2,3）
    x = inputs["x"]
    y = inputs["y"]

    # 今回規定：2つなら add
    plan_config = {
        "steps": [
            {
                "name": "add",
                "op": "add",
                "inputs": {"x": "x", "y": "y"},  # param -> logical
                "outputs": ["sum"],
            }
        ]
    }
    return {"plan": plan_config}


def register(registry) -> None:
    registry.register("plan_from_two_numbers", plan_from_two_numbers_op)
