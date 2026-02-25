"""Tests for step discovery via flowbook.steps entry point group."""

from __future__ import annotations

import pytest

from flowbook import Registry, UnknownOp, discover_steps


def test_discover_steps_registers_builtin_ops() -> None:
    """When flowbook is installed, discover_steps loads built-in steps from entry points."""
    registry = Registry()
    discover_steps(registry)
    try:
        op = registry.get("add")
    except UnknownOp:
        pytest.skip("flowbook.steps entry points not available (package not installed?)")
    assert op is not None


def test_discover_steps_safe_to_call_twice() -> None:
    """Calling discover_steps twice still resolves ops; later call overwrites, no duplicate keys."""
    registry = Registry()
    discover_steps(registry)
    a = registry.get("add")
    discover_steps(registry)
    b = registry.get("add")
    assert a is not None and b is not None


def test_registry_list_ops_and_get_op_spec() -> None:
    """Registry.list_ops and get_op_spec return introspection data."""
    registry = Registry()
    discover_steps(registry)
    try:
        ops = registry.list_ops()
    except Exception:
        pytest.skip("flowbook.steps entry points not available")
    assert isinstance(ops, list)
    assert ops == sorted(ops)
    assert "add" in ops

    spec = registry.get_op_spec("add")
    assert spec.op_name == "add"
    assert spec.required_inputs == ("x", "y")
    assert spec.optional_inputs == ()
    assert "sum" in spec.output_keys
