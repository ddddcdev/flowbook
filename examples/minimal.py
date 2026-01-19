from __future__ import annotations

import uuid

from flowbook.artifacts.store import InMemoryArtifactsStore
from flowbook.registry.registry import Registry
from flowbook.runtime.build import build
from flowbook.runtime.context import RunContext
from flowbook.runtime.inspect import inspect
from flowbook.runtime.run import run


def main() -> None:
    # --- Setup (apps responsibility in real usage)
    store = InMemoryArtifactsStore()
    registry = Registry()

    # Seed input artifacts
    store.put("artifact:input/x", 2)
    store.put("artifact:input/y", 3)

    # Register ops
    def add_op(inputs: dict, store_):
        return {"sum": inputs["x"] + inputs["y"]}

    registry.register("add", add_op)

    # --- Flowbook minimal contract
    profile = inspect({"note": "opaque"})
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
    pipeline = build(profile, config)

    run_id = str(uuid.uuid4())
    ctx = RunContext(
        run_id=run_id, store=store, registry=registry, meta={"env": "local"}
    )
    info = run(pipeline, ctx)

    # --- Observe
    print("run_info:", info)
    print("artifacts keys:", store.list())
    out_key = info.steps[0].outputs["sum"]
    print("sum key:", out_key)
    print("sum value:", store.get(out_key))


if __name__ == "__main__":
    main()
