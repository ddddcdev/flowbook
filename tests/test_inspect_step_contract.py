from __future__ import annotations

from flowbook.artifacts.memory_store import InMemoryArtifactsStore
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry


def test_inspect_step_writes_control_artifacts() -> None:
    store = InMemoryArtifactsStore()
    registry = Registry()
    register_steps(registry)

    config = {
        "steps": [
            {
                "name": "inspect",
                "op": "inspect",
                "inputs": {"source_uri": "source_uri", "read_spec": "read_spec"},
            }
        ]
    }

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    run = engine.prepare()

    # inputs は run 内へ投入（bindingsはrunが内部で保持する想定）
    run.put_input("source_uri", "/tmp/dummy.xlsx")
    run.put_input("read_spec", {"sheet": 0})

    info = run.exec(config=config)
    assert info.status == "succeeded"

    inspect_key = info.steps[0].outputs["inspect_result"]
    r = run.get(inspect_key)
    assert r["source_uri"] == "/tmp/dummy.xlsx"
    assert "warnings" in r
    assert "suggested_read_spec" in r
