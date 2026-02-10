from __future__ import annotations

import pytest

from flowbook.artifacts.memory_store import InMemoryArtifactsStore

pytestmark = pytest.mark.integration
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry


def test_planner_produces_plan_output_then_engine_executes_plan() -> None:
    """
    Day10 pattern:
    1) Planner step produces a plan config dict as output (not global PLAN)
    2) Plan is persisted and artifact key recorded in StepRunInfo.outputs["plan"]
    3) exec_with_plan_once reads plan from that artifact and executes it
    """
    store = InMemoryArtifactsStore()
    registry = Registry()
    register_steps(registry)

    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_two_numbers",
                "inputs": {"x": "x", "y": "y"},
            }
        ]
    }

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    run = engine.prepare()

    run.put_input("x", 2)
    run.put_input("y", 3)

    info1, info2 = run.exec_with_plan_once(planner_config=planner_config)

    # ✅ Verify planner step produced plan output
    assert info1.status == "succeeded"
    assert len(info1.steps) == 1
    planner_step = info1.steps[0]
    assert planner_step.name == "planner"
    assert "plan" in planner_step.outputs

    # ✅ Load plan from artifact (traceable via StepRunInfo)
    plan_key = planner_step.outputs["plan"]
    plan = run.get(plan_key)

    assert isinstance(plan, dict)
    assert "steps" in plan
    assert plan["steps"][0]["op"] == "add"
    assert plan["steps"][0]["inputs"] == {"x": "x", "y": "y"}

    # ✅ Verify plan execution produced expected output
    assert info2.status == "succeeded"
    assert len(info2.steps) == 1
    assert info2.steps[0].name == "add"

    out_sum_key = info2.steps[0].outputs["sum"]
    assert run.get(out_sum_key) == 5
