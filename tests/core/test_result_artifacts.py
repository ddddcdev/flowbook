"""
Tests for result_artifacts: plan-level declaration of main result artifact paths.
"""

from __future__ import annotations

import pytest

from flowbook import (
    Engine,
    InMemoryArtifactsStore,
    InMemoryConfigStore,
    Registry,
    register_steps,
)
from flowbook.core.configs.spec_types import Plan
from flowbook.core.runtime.build import build
from flowbook.core.runtime.executor import ResultArtifactsValidationError

pytestmark = pytest.mark.e2e


def test_build_plan_with_result_artifacts() -> None:
    """Plan config with result_artifacts produces Plan with result_artifacts."""
    plan_config = {
        "steps": [
            {"name": "add", "op": "add", "inputs": {"x": 1, "y": 2}},
        ],
        "result_artifacts": [
            {"step": "add", "key": "sum"},
        ],
    }
    plan = build(plan_config)
    assert plan.result_artifacts is not None
    assert len(plan.result_artifacts) == 1
    assert plan.result_artifacts[0].path == "add/sum"
    assert plan.result_artifacts[0].label is None


def test_build_plan_with_result_artifacts_and_labels() -> None:
    """result_artifacts supports optional label."""
    plan_config = {
        "steps": [{"name": "add", "op": "add", "inputs": {"x": 1, "y": 2}}],
        "result_artifacts": [
            {"step": "add", "key": "sum", "label": "Total"},
        ],
    }
    plan = build(plan_config)
    assert plan.result_artifacts is not None
    assert plan.result_artifacts[0].label == "Total"


def test_build_plan_without_result_artifacts() -> None:
    """Plan without result_artifacts has result_artifacts=None."""
    plan_config = {
        "steps": [{"name": "add", "op": "add", "inputs": {"x": 1, "y": 2}}],
    }
    plan = build(plan_config)
    assert plan.result_artifacts is None


def test_exec_plan_with_result_artifacts_succeeds() -> None:
    """exec_plan with result_artifacts runs and uses declared paths."""
    store = InMemoryArtifactsStore()
    registry = Registry()
    register_steps(registry)

    plan_config = {
        "steps": [
            {
                "name": "add",
                "op": "add",
                "inputs": {"x": "@x", "y": "@y"},
            }
        ],
        "result_artifacts": [{"step": "add", "key": "sum", "label": "Sum"}],
    }

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    with engine.create_run() as run:
        run.put_input("x", 2)
        run.put_input("y", 3)
        info = run.exec_plan(plan_config=plan_config)

    assert info.status == "succeeded"
    assert len(info.steps) == 1
    assert info.steps[0].outputs["sum"]
    assert run.get(info.steps[0].outputs["sum"]) == 5


def test_build_result_artifacts_invalid_entry_raises() -> None:
    """result_artifacts entry without step/key raises."""
    plan_config = {
        "steps": [{"name": "add", "op": "add", "inputs": {"x": 1, "y": 2}}],
        "result_artifacts": [{"label": "only label"}],
    }
    with pytest.raises(ValueError, match="result_artifacts entry must have step and key"):
        build(plan_config)


def test_exec_plan_result_artifacts_path_not_produced_raises() -> None:
    """RuntimeError when result_artifacts path is not produced by any step."""
    store = InMemoryArtifactsStore()
    registry = Registry()
    register_steps(registry)

    plan_config = {
        "steps": [
            {
                "name": "add",
                "op": "add",
                "inputs": {"x": "@x", "y": "@y"},
            }
        ],
        "result_artifacts": [{"step": "add", "key": "nonexistent"}],
    }

    engine = Engine(store=store, registry=registry, meta={"env": "test"})
    with engine.create_run() as run:
        run.put_input("x", 2)
        run.put_input("y", 3)
        with pytest.raises(
            ResultArtifactsValidationError, match="result_artifacts path .* not produced"
        ):
            run.exec_plan(plan_config=plan_config)


def test_load_plan_with_result_artifacts_passes_through() -> None:
    """load_plan includes result_artifacts in output; exec merges and runs."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    plan_spec = {
        "plan": {
            "name": "plan_add",
            "steps": [
                {
                    "name": "add",
                    "op": "add",
                    "inputs": {"x": "@x", "y": "@y"},
                }
            ],
        },
        "result_artifacts": [{"step": "add", "key": "sum", "label": "Total"}],
    }
    config_store.put_spec(
        Plan,
        "plan_add",
        plan_spec,
        config_id="test_config_v1",
    )

    registry = Registry()
    register_steps(registry)
    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
        meta={"env": "test"},
    )

    with engine.create_run() as run:
        run.put_input("x", 2)
        run.put_input("y", 3)
        run.put_input("plan_name", "plan_add")

        planner_config = {
            "steps": [
                {
                    "name": "planner",
                    "op": "load_plan",
                    "inputs": {"plan_name": "@plan_name"},
                }
            ]
        }

        info1, info2 = run.exec_with_planner_once(planner_config=planner_config)

        assert info1.status == "succeeded"
        assert "result_artifacts" in info1.steps[0].outputs
        assert info2.status == "succeeded"
        assert run.get(info2.steps[0].outputs["sum"]) == 5
