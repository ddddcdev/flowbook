from __future__ import annotations

from flowbook.artifacts.keys import INSPECT_RESULT, SOURCE_URI
from flowbook.artifacts.store import InMemoryArtifactsStore
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry


def test_inspect_step_writes_control_artifacts() -> None:
    store = InMemoryArtifactsStore()
    registry = Registry()
    register_steps(registry)

    store.put(SOURCE_URI, "/tmp/dummy.xlsx")

    config = {
        "steps": [
            {
                "name": "inspect",
                "op": "inspect",
                "inputs": {
                    "source_uri": SOURCE_URI,
                    "read_spec": "artifact:input/read_spec",
                },
                "outputs": [],
            }
        ]
    }

    # read_specは未指定でも動くようにしているが、ここでは一応置く
    store.put("artifact:input/read_spec", {"sheet": 0})

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    engine.execute(config=config)

    r = store.get(INSPECT_RESULT)

    print(r)

    assert r["source_uri"] == "/tmp/dummy.xlsx"
    assert "warnings" in r
    assert "suggested_read_spec" in r
