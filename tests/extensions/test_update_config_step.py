"""Tests for update_config step: put_spec from step to ConfigStore."""

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
from flowbook.core.configs.validation import validate_spec
from flowbook.extensions.steps.add import AddOp
from flowbook.extensions.steps.load_plan import LoadPlanOp
from flowbook.extensions.steps.update_config import UpdateConfigOp

pytestmark = pytest.mark.e2e


def test_validate_spec_accepts_valid_specs() -> None:
    """validate_spec passes for specs with required keys."""
    validate_spec("plan", {"plan": {"steps": []}})
    validate_spec("input_profile", {"kind_rules": []})
    validate_spec("mapping", {"ops": []})
    validate_spec("lookup_table", {"artifact_key": "some_key"})
    validate_spec("entity_plan_map", {"map": {"a": "b"}, "default": None})


def test_validate_spec_raises_for_missing_keys() -> None:
    """validate_spec raises ValueError when required keys are missing."""
    with pytest.raises(ValueError, match="missing required keys"):
        validate_spec("plan", {})
    with pytest.raises(ValueError, match="kind_rules"):
        validate_spec("input_profile", {})
    with pytest.raises(ValueError, match="unknown kind"):
        validate_spec("unknown", {})


def test_update_config_roundtrip() -> None:
    """update_config writes spec; get_spec roundtrip verifies."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    # Use literal values (no @ refs) to avoid preflight requiring x,y bindings
    plan_spec = {
        "plan": {
            "name": "plan_add",
            "steps": [
                {
                    "name": "add",
                    "op": "add",
                    "inputs": {AddOp.Inputs.X: 1, AddOp.Inputs.Y: 2},
                }
            ],
        }
    }

    with engine.create_run() as run:
        info = run.exec_plan(
            plan_config={
                "steps": [
                    {
                        "name": "writer",
                        "op": "update_config",
                        "inputs": {
                            UpdateConfigOp.Inputs.KIND: "plan",
                            UpdateConfigOp.Inputs.NAME: "plan_add",
                            UpdateConfigOp.Inputs.SPEC: plan_spec,
                        },
                    }
                ]
            }
        )

    assert info.status == "succeeded", f"failed: {info.errors}"
    assert len(info.steps) == 1
    step_info = info.steps[0]
    assert step_info.name == "writer"
    assert step_info.status == "succeeded"
    assert UpdateConfigOp.Outputs.CONFIG_ID in step_info.outputs
    assert run.get(step_info.outputs[UpdateConfigOp.Outputs.KIND]) == "plan"
    assert run.get(step_info.outputs[UpdateConfigOp.Outputs.NAME]) == "plan_add"

    # Roundtrip: read back via ConfigStore
    loaded = config_store.get_spec(Plan, "plan_add")
    assert loaded["plan"]["steps"][0]["inputs"] == {
        AddOp.Inputs.X: 1,
        AddOp.Inputs.Y: 2,
    }


def test_update_config_then_load_plan_in_same_run() -> None:
    """update_config writes plan; load_plan reads it; verify chain."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    # Use literal values to avoid ref collection from nested spec
    plan_spec = {
        "plan": {
            "name": "plan_add",
            "steps": [
                {
                    "name": "add",
                    "op": "add",
                    "inputs": {AddOp.Inputs.X: 10, AddOp.Inputs.Y: 20},
                }
            ],
        }
    }

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    with engine.create_run() as run:
        info = run.exec_plan(
            plan_config={
                "steps": [
                    {
                        "name": "writer",
                        "op": "update_config",
                        "inputs": {
                            UpdateConfigOp.Inputs.KIND: "plan",
                            UpdateConfigOp.Inputs.NAME: "plan_add",
                            UpdateConfigOp.Inputs.SPEC: plan_spec,
                        },
                    },
                    {
                        "name": "reader",
                        "op": "load_plan",
                        "inputs": {LoadPlanOp.Inputs.PLAN_NAME: "plan_add"},
                    },
                ]
            }
        )

    assert info.status == "succeeded", f"failed: {info.errors}"
    assert len(info.steps) == 2
    reader_step = info.steps[1]
    assert reader_step.name == "reader"
    assert LoadPlanOp.Outputs.PLAN in reader_step.outputs

    plan_key = reader_step.outputs[LoadPlanOp.Outputs.PLAN]
    plan = run.get_dict(plan_key)
    assert plan["steps"][0]["op"] == "add"
    assert plan["steps"][0]["inputs"] == {
        AddOp.Inputs.X: 10,
        AddOp.Inputs.Y: 20,
    }


def test_update_config_unknown_kind_raises() -> None:
    """Unknown kind causes plan to fail with helpful error in info.errors."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    with engine.create_run() as run:
        info = run.exec_plan(
            plan_config={
                "steps": [
                    {
                        "name": "writer",
                        "op": "update_config",
                        "inputs": {
                            UpdateConfigOp.Inputs.KIND: "unknown_kind",
                            UpdateConfigOp.Inputs.NAME: "foo",
                            UpdateConfigOp.Inputs.SPEC: {},
                        },
                    }
                ]
            }
        )

    assert info.status == "failed"
    assert len(info.errors) >= 1
    assert "unknown" in info.errors[0].lower() or "unknown_kind" in info.errors[0]


def test_update_config_missing_required_keys_fails() -> None:
    """Spec missing required keys causes plan to fail with validation error."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    with engine.create_run() as run:
        info = run.exec_plan(
            plan_config={
                "steps": [
                    {
                        "name": "writer",
                        "op": "update_config",
                        "inputs": {
                            UpdateConfigOp.Inputs.KIND: "plan",
                            UpdateConfigOp.Inputs.NAME: "bad_plan",
                            UpdateConfigOp.Inputs.SPEC: {},  # missing "plan" key
                        },
                    }
                ]
            }
        )

    assert info.status == "failed"
    assert len(info.errors) >= 1
    assert "missing" in info.errors[0].lower() or "required" in info.errors[0].lower()


def test_update_config_config_id_optional() -> None:
    """When config_id omitted, step generates UUID and returns it."""
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    with engine.create_run() as run:
        info = run.exec_plan(
            plan_config={
                "steps": [
                    {
                        "name": "writer",
                        "op": "update_config",
                        "inputs": {
                            UpdateConfigOp.Inputs.KIND: "plan",
                            UpdateConfigOp.Inputs.NAME: "auto_id_plan",
                            UpdateConfigOp.Inputs.SPEC: {"plan": {"steps": []}},
                        },
                    }
                ]
            }
        )

    assert info.status == "succeeded"
    step_info = info.steps[0]
    config_id_key = step_info.outputs[UpdateConfigOp.Outputs.CONFIG_ID]
    config_id = run.get(config_id_key)
    assert isinstance(config_id, str)
    assert len(config_id) == 36  # UUID string format
