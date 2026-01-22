from __future__ import annotations

from flowbook.artifacts.store import InMemoryArtifactsStore
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry


def test_extensions_register_and_engine_execute() -> None:
    store = InMemoryArtifactsStore()
    registry = Registry()

    store.put("artifact:input/x", 2)
    store.put("artifact:input/y", 3)

    register_steps(registry)

    config = {
        "steps": [
            {
                "name": "s1",
                "op": "add",
                "inputs": {"x": "artifact:input/x", "y": "artifact:input/y"},
                "outputs": ["sum"],
            }
        ]
    }

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    _, info = engine.execute(config=config)

    out_key = info.steps[0].outputs["sum"]
    assert store.get(out_key) == 5
