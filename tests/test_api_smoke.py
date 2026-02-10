# import pytest
# pytestmark = pytest.mark.smoke
# from fastapi.testclient import TestClient

# from apps.api.app.main import app


# def test_api_smoke_inspect_build_run_and_artifacts_roundtrip():
#     client = TestClient(app)

#     # 1) inspect
#     r = client.post("/inspect", json={"input": {"note": "opaque"}})
#     assert r.status_code == 200
#     profile = r.json()["profile"]

#     # 2) build
#     config = {
#         "steps": [
#             {
#                 "name": "s1",
#                 "op": "add",
#                 "inputs": {"x": "artifact:input/x", "y": "artifact:input/y"},
#             }
#         ]
#     }
#     r = client.post("/build", json={"profile": profile, "config": config})
#     assert r.status_code == 200
#     body = r.json()
#     pipeline_id = body["pipeline_id"]
#     assert isinstance(pipeline_id, str) and len(pipeline_id) > 0

#     # Seed artifacts (this endpoint can be added later).
#     # For now directly via /artifacts/{key} PUT is also OK,
#     # but since it's not in your plan, the app should pre-seed in-memory for smoke test
#     # OR provide a minimal seed route.
#     # For now, require app startup to seed:
#     # artifact:input/x = 2, artifact:input/y = 3

#     # 3) run
#     r = client.post(
#         "/run", json={"pipeline_id": pipeline_id, "ctx": {"meta": {"env": "test"}}}
#     )

#     assert r.status_code == 200
#     run_info = r.json()["run_info"]

#     if run_info["status"] != "succeeded":
#         raise AssertionError(run_info)

#     assert run_info["status"] == "succeeded"
#     out_key = run_info["steps"][0]["outputs"]["sum"]
#     assert isinstance(out_key, str)

#     # 4) list artifacts
#     r = client.get("/artifacts")
#     assert r.status_code == 200
#     keys = r.json()["keys"]
#     assert out_key in keys

#     # 5) get artifact
#     r = client.get(f"/artifacts/{out_key}")
#     assert r.status_code == 200
#     assert r.json()["value"] == 5
