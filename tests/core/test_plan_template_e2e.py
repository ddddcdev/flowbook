from __future__ import annotations

import pytest

from flowbook import (
    Engine,
    InMemoryArtifactsStore,
    InMemoryConfigStore,
    Registry,
    register_steps,
)
from flowbook.core.configs.spec_types import PlanTemplate
from flowbook.extensions.steps.add import AddOp
from flowbook.extensions.steps.plan_from_template import PlanFromTemplateOp

pytestmark = pytest.mark.e2e


def test_plan_from_template_reads_template_from_config_store() -> None:
    """
    Plan templates loaded from ConfigStore via RunStore.configs.

    Scenario:
    1. Store a plan template in ConfigStore (kind="plan_template", name="tmpl_add")
    2. Use plan_from_template step to load and return the template's plan
    3. Execute that plan (add operation) with inputs x=2, y=3
    4. Verify planner output and final result (sum=5)
    """
    # ---- Setup ----
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    # ---- Put template in config store ----
    template_spec = {
        "plan": {
            "steps": [
                {
                    "name": "add",
                    "op": "add",
                    "inputs": {AddOp.Inputs.X: "x", AddOp.Inputs.Y: "y"},
                }
            ]
        }
    }
    config_store.put_spec(
        PlanTemplate,
        "tmpl_add",
        template_spec,
        config_id="test_config_v1",
    )

    # ---- Create engine with config store ----
    engine = Engine(
        store=artifacts_store, registry=registry, config_store=config_store, meta={"env": "test"}
    )
    run = engine.prepare()

    # ---- Set inputs ----
    run.put_input("x", 2)
    run.put_input("y", 3)
    run.put_input("template_name", "tmpl_add")

    # ---- Planner config: use plan_from_template ----
    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {PlanFromTemplateOp.Inputs.TEMPLATE_NAME: "template_name"},
            }
        ]
    }

    # ---- Execute: planner + plan ----
    info1, info2 = run.exec_with_plan_once(planner_config=planner_config)

    # ✅ Verify planner step succeeded and produced plan output
    assert info1.status == "succeeded", f"planner failed: {info1.errors}"
    assert len(info1.steps) == 1
    planner_step = info1.steps[0]
    assert planner_step.name == "planner"
    assert planner_step.status == "succeeded"
    assert PlanFromTemplateOp.Outputs.PLAN in planner_step.outputs, (
        f"plan not in outputs: {planner_step.outputs}"
    )

    # ✅ Load and verify plan from artifact
    plan_key = planner_step.outputs[PlanFromTemplateOp.Outputs.PLAN]
    plan = run.get_dict(plan_key)

    assert isinstance(plan, dict), f"plan should be dict, got {type(plan).__name__}"
    assert "steps" in plan
    assert len(plan["steps"]) == 1
    assert plan["steps"][0]["name"] == "add"
    assert plan["steps"][0]["op"] == "add"
    assert plan["steps"][0]["inputs"] == {AddOp.Inputs.X: "x", AddOp.Inputs.Y: "y"}

    # ✅ Verify plan execution succeeded
    assert info2.status == "succeeded", f"plan execution failed: {info2.errors}"
    assert len(info2.steps) == 1
    add_step = info2.steps[0]
    assert add_step.name == "add"
    assert add_step.status == "succeeded"
    assert AddOp.Outputs.SUM in add_step.outputs

    # ✅ Verify final result (2 + 3 = 5)
    sum_key = add_step.outputs[AddOp.Outputs.SUM]
    result = run.get(sum_key)
    assert result == 5, f"expected 5, got {result}"


def test_plan_from_template_missing_template_name() -> None:
    """
    Verify clear error when template_name is not provided in inputs.
    """
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    run = engine.prepare()

    # Missing template_name input
    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {},  # ← No template_name
            }
        ]
    }

    try:
        run.exec_with_plan_once(planner_config=planner_config)
        raise AssertionError("should raise error for missing template_name")
    except RuntimeError as e:
        assert "planner run failed" in str(e)


def test_plan_from_template_template_not_found() -> None:
    """
    Verify clear error when template is not in ConfigStore.
    """
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    run = engine.prepare()
    run.put_input("template_name", "nonexistent_template")

    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {PlanFromTemplateOp.Inputs.TEMPLATE_NAME: "template_name"},
            }
        ]
    }

    try:
        run.exec_with_plan_once(planner_config=planner_config)
        raise AssertionError("should raise error for missing template")
    except RuntimeError as e:
        assert "planner run failed" in str(e)


def test_plan_from_template_missing_plan_key() -> None:
    """
    Verify clear error when template spec doesn't have "plan" key.
    """
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    # Put template without "plan" key
    config_store.put_spec(
        PlanTemplate,
        "bad_template",
        {"description": "missing plan"},  # ← No "plan" key
        config_id="test_config_v1",
    )

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    run = engine.prepare()
    run.put_input("template_name", "bad_template")

    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {PlanFromTemplateOp.Inputs.TEMPLATE_NAME: "template_name"},
            }
        ]
    }

    try:
        run.exec_with_plan_once(planner_config=planner_config)
        raise AssertionError("should raise error for missing plan key")
    except RuntimeError as e:
        assert "planner run failed" in str(e)


def test_plan_from_template_plan_not_dict() -> None:
    """
    Verify clear error when plan value is not a dict.
    """
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    # Put template with plan as non-dict
    config_store.put_spec(
        PlanTemplate,
        "bad_plan_template",
        {"plan": "not a dict"},  # ← plan is string, not dict
        config_id="test_config_v1",
    )

    engine = Engine(
        store=artifacts_store,
        registry=registry,
        config_store=config_store,
    )
    run = engine.prepare()
    run.put_input("template_name", "bad_plan_template")

    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {PlanFromTemplateOp.Inputs.TEMPLATE_NAME: "template_name"},
            }
        ]
    }

    try:
        run.exec_with_plan_once(planner_config=planner_config)
        raise AssertionError("should raise error for non-dict plan")
    except RuntimeError as e:
        assert "planner run failed" in str(e)


def test_preflight_validates_required_inputs_in_plan_execution() -> None:
    """
    Preflight validation: plan execution fails fast if referenced inputs are missing.

    Scenario:
    1. Store a plan template requiring x and y inputs
    2. Planner produces the plan successfully with template_name only
    3. Plan execution should fail at preflight validation (missing x, y)
    4. Error message includes run_id, missing keys, and step references
    """
    artifacts_store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()

    registry = Registry()
    register_steps(registry)

    # Put template requiring x and y
    template_spec = {
        "plan": {
            "steps": [
                {
                    "name": "add",
                    "op": "add",
                    "inputs": {AddOp.Inputs.X: "x", AddOp.Inputs.Y: "y"},  # requires x, y
                }
            ]
        }
    }
    config_store.put_spec(
        PlanTemplate,
        "tmpl_add",
        template_spec,
        config_id="test_config_v1",
    )

    engine = Engine(
        store=artifacts_store, registry=registry, config_store=config_store, meta={"env": "test"}
    )
    run = engine.prepare()

    # Set only template_name; omit x and y
    run.put_input("template_name", "tmpl_add")

    planner_config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {PlanFromTemplateOp.Inputs.TEMPLATE_NAME: "template_name"},
            }
        ]
    }

    try:
        run.exec_with_plan_once(planner_config=planner_config)
        raise AssertionError("should fail at plan execution preflight due to missing x, y")
    except RuntimeError as e:
        error_str = str(e)
        # Verify error message content
        assert "missing required input" in error_str, (
            f"error should mention missing inputs: {error_str}"
        )
        assert "run_id=" in error_str, f"error should include run_id: {error_str}"
        # Check that both missing keys are mentioned
        assert "'x'" in error_str, f"error should mention missing key 'x': {error_str}"
        assert "'y'" in error_str, f"error should mention missing key 'y': {error_str}"
        # Verify that "add" step is referenced
        assert "add" in error_str, f"error should reference 'add' step: {error_str}"
