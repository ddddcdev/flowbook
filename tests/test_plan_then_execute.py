from __future__ import annotations

from flowbook.artifacts.keys import PLAN
from flowbook.artifacts.store import InMemoryArtifactsStore
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry


def test_inspect_produces_plan_then_engine_executes_plan() -> None:
    store = InMemoryArtifactsStore()
    registry = Registry()
    register_steps(registry)

    # 入力（2つの数字）
    store.put("artifact:input/x", 2)
    store.put("artifact:input/y", 3)

    # Step1: inspect/planner だけ走るconfig
    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_two_numbers",
                "inputs": {"x": "artifact:input/x", "y": "artifact:input/y"},
                "outputs": [],
            }
        ]
    }

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    rid, info1, info2 = engine.execute_with_plan_once(planner_config=planner_config)

    # Planが出ている
    plan = store.get(PLAN)
    assert plan["steps"][0]["op"] == "add"

    print("info2:", info2)
    print("step0 outputs field:", info2.steps[0].outputs)
    print("store keys:", store.list())

    # Plan実行結果が出ている
    out_sum_key = info2.steps[0].outputs["sum"]
    assert store.get(out_sum_key) == 5
