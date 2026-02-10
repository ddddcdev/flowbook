"""
Preflight validation: unregistered op, missing required inputs, surplus inputs.
Error messages must include run_id, step name, and missing/surplus keys.
"""

from __future__ import annotations

import pytest

from flowbook.artifacts.memory_store import InMemoryArtifactsStore
from flowbook.configs.memory_store import InMemoryConfigStore
from flowbook.engine.engine import Engine
from flowbook.registry.extensions import register_steps
from flowbook.registry.registry import Registry

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
    info = run.exec(pipeline_config=config)
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
    run.put_input("template_name", "some_tmpl")

    config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {},  # missing template_name
            }
        ]
    }
    info = run.exec(pipeline_config=config)
    assert info.status == "failed"
    # Either preflight (PortSpec) or binding validation catches it
    assert "missing" in info.errors[0].lower() or "template_name" in info.errors[0]
    assert "planner" in info.errors[0]


def test_preflight_surplus_input_raises_with_step_and_keys() -> None:
    store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    registry = Registry()
    register_steps(registry)

    engine = Engine(store=store, registry=registry, config_store=config_store)
    run = engine.prepare()
    run.put_input("template_name", "tmpl_add")
    run.put_input("extra_thing", "x")

    config = {
        "steps": [
            {
                "name": "planner",
                "op": "plan_from_template",
                "inputs": {"template_name": "template_name", "surplus_key": "extra_thing"},
            }
        ]
    }
    info = run.exec(pipeline_config=config)
    assert info.status == "failed"
    assert "surplus" in info.errors[0].lower()
    assert "planner" in info.errors[0]
    assert "surplus_key" in info.errors[0]
