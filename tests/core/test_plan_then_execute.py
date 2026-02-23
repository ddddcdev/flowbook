from __future__ import annotations

import pytest

from flowbook import Engine, InMemoryArtifactsStore, Registry, register_steps
from flowbook.extensions.steps.add import AddOp
from flowbook.extensions.steps.plan_from_two_numbers import PlanFromTwoNumbersOp

pytestmark = pytest.mark.integration


def test_planner_produces_plan_output_then_engine_executes_plan() -> None:
    """
    Day10 pattern:
    1) Planner step produces a plan config dict as output (not global PLAN)
    2) Plan is persisted and artifact key recorded in StepRunInfo.outputs["plan"]
    3) exec_with_planner_once reads plan from that artifact and executes it
    """
    store = InMemoryArtifactsStore()
    registry = Registry()
    register_steps(registry)

    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_two_numbers",
                "inputs": {"x": "@x", "y": "@y"},
            }
        ]
    }

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    with engine.create_run() as run:
        run.put_input("x", 2)
        run.put_input("y", 3)

        info1, info2 = run.exec_with_planner_once(planner_config=planner_config)

        # ✅ Verify planner step produced plan output
        assert info1.status == "succeeded"
        assert len(info1.steps) == 1
        planner_step = info1.steps[0]
        assert planner_step.name == "planner"
        assert PlanFromTwoNumbersOp.Outputs.PLAN in planner_step.outputs

        # ✅ Load plan from artifact (traceable via StepRunInfo)
        plan_key = planner_step.outputs[PlanFromTwoNumbersOp.Outputs.PLAN]
        plan = run.get_dict(plan_key)

        assert isinstance(plan, dict)
        assert "steps" in plan
        assert plan["steps"][0]["op"] == "add"
        assert plan["steps"][0]["inputs"] == {AddOp.Inputs.X: "@x", AddOp.Inputs.Y: "@y"}

        # ✅ Verify plan execution produced expected output
        assert info2.status == "succeeded"
        assert len(info2.steps) == 1
        assert info2.steps[0].name == "add"

        out_sum_key = info2.steps[0].outputs[AddOp.Outputs.SUM]
        assert run.get(out_sum_key) == 5
