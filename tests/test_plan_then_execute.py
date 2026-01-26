from __future__ import annotations

from flowbook.artifacts.keys import PLAN
from flowbook.artifacts.scoped import RunScopedStore
from flowbook.artifacts.store import InMemoryArtifactsStore
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry


def test_inspect_produces_plan_then_engine_executes_plan() -> None:
    store = InMemoryArtifactsStore()
    registry = Registry()
    register_steps(registry)

    # planner stepのinputsは論理名
    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_two_numbers",
                "inputs": {"x": "x", "y": "y"},  # param -> logical
                "outputs": [],
            }
        ]
    }

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    run = engine.prepare()

    run.put_input("x", 2)
    run.put_input("y", 3)

    info1, info2 = run.exec_with_plan_once(planner_config=planner_config)

    plan = run.get(PLAN)

    assert plan["steps"][0]["op"] == "add"
    assert plan["steps"][0]["inputs"] == {"x": "x", "y": "y"}

    out_sum_key = info2.steps[0].outputs["sum"]
    assert run.get(out_sum_key) == 5
