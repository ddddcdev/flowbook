"""
Preflight validation: unregistered op, missing required inputs, surplus inputs.
Error messages must include run_id, step name, and missing/surplus keys.
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
from flowbook.extensions.steps.plan_from_template import PlanFromTemplateOp

pytestmark = pytest.mark.unit


def test_preflight_unregistered_op_raises_with_run_id_and_step_name() -> None:
    store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    registry = Registry()
    register_steps(registry)

    engine = Engine(store=store, registry=registry, config_store=config_store)
    run = engine.prepare()

    config = {
        "steps": [
            {"name": "s1", "op": "nonexistent_op", "inputs": {}},
        ]
    }
    info = run.exec_plan(plan_config=config)
    assert info.status == "failed"
    assert run.run_id
    assert "unregistered op" in info.errors[0]
    assert "run_id=" in info.errors[0]
    assert "s1" in info.errors[0]
    assert "nonexistent_op" in info.errors[0]


def test_preflight_missing_required_input_raises_with_step_and_keys() -> None:
    store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    registry = Registry()
    register_steps(registry)

    engine = Engine(store=store, registry=registry, config_store=config_store)
    run = engine.prepare()
    run.put_input(PlanFromTemplateOp.Inputs.TEMPLATE_NAME, "some_tmpl")

    config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {},  # missing template_name
            }
        ]
    }
    info = run.exec_plan(plan_config=config)
    assert info.status == "failed"
    # Either preflight (op.Inputs) or binding validation catches it
    err = info.errors[0]
    assert "missing" in err.lower() or PlanFromTemplateOp.Inputs.TEMPLATE_NAME in err
    assert "planner" in err


def test_preflight_surplus_input_raises_with_step_and_keys() -> None:
    store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    registry = Registry()
    register_steps(registry)

    engine = Engine(store=store, registry=registry, config_store=config_store)
    run = engine.prepare()
    run.put_input(PlanFromTemplateOp.Inputs.TEMPLATE_NAME, "tmpl_add")
    run.put_input("extra_thing", "x")

    config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {
                    PlanFromTemplateOp.Inputs.TEMPLATE_NAME: "template_name",
                    "surplus_key": "extra_thing",
                },
            }
        ]
    }
    info = run.exec_plan(plan_config=config)
    assert info.status == "failed"
    assert "surplus" in info.errors[0].lower()
    assert "planner" in info.errors[0]
    assert "surplus_key" in info.errors[0]
