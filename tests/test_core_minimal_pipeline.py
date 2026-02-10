# import pytest
# pytestmark = pytest.mark.unit
# import uuid

# from flowbook.artifacts.store import InMemoryArtifactsStore
# from flowbook.registry.registry import Registry
# from flowbook.runtime.context import RunContext
# from flowbook.runtime.inspect import inspect
# from flowbook.runtime.build import build
# from flowbook.runtime.run import run


# def test_core_minimal_pipeline_serial_run_writes_artifacts_and_returns_run_info_only():
#     # --- Arrange
#     store = InMemoryArtifactsStore()
#     registry = Registry()

#     # Seed input artifacts (apps responsibility in real usage)
#     store.put("artifact:input/x", 2)
#     store.put("artifact:input/y", 3)

#     # Register minimal op
#     def add_op(inputs: dict, store_):
#         return {"sum": inputs["x"] + inputs["y"]}

#     registry.register("add", add_op)

#     raw_input = {"note": "opaque"}
#     profile = inspect(raw_input)

#     config = {
#         "steps": [
#             {
#                 "name": "s1",
#                 "op": "add",
#                 "inputs": {"x": "artifact:input/x", "y": "artifact:input/y"},
#             }
#         ]
#     }

#     pipeline = build(profile, config)

#     run_id = str(uuid.uuid4())
#     ctx = RunContext(run_id=run_id, store=store, registry=registry, meta={"env": "test"})

#     # --- Act
#     info = run(pipeline, ctx)

#     # --- Assert: run_info has no real data, only keys & metadata
#     assert info.run_id == run_id
#     assert info.status == "succeeded"
#     assert len(info.steps) == 1

#     step = info.steps[0]
#     assert step.name == "s1"
#     assert step.status == "succeeded"
#     assert step.inputs == {"x": "artifact:input/x", "y": "artifact:input/y"}

#     # outputs are artifact keys (not embedded values)
#     out_key = step.outputs["sum"]
#     assert isinstance(out_key, str)
#     assert out_key.startswith(f"artifact:{run_id}/s1/sum")

#     # artifacts contain the real data
#     assert store.get(out_key) == 5

#     # run_info must not contain embedded payloads (guardrail)
#     # (If you later add fields, keep them to metadata only)
#     assert "value" not in str(info).lower()
