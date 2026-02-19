"""
Resolve step inputs: refs (@<logical_address>) via bindings -> store.get_any; literals unchanged.
Recursively resolves dict/list; keys are untouched. Only str starting with @ is a ref.
"""

from __future__ import annotations

from typing import Any

from flowbook.core.runtime.context import RunContext


def _collect_refs(value: Any) -> set[str]:
    """Collect all logical addresses (ref payloads) that appear as refs in value."""
    refs: set[str] = set()
    if isinstance(value, str) and value.startswith("@"):
        refs.add(value[1:])
        return refs
    if isinstance(value, list):
        for item in value:
            refs |= _collect_refs(item)
        return refs
    if isinstance(value, dict):
        for v in value.values():
            refs |= _collect_refs(v)
        return refs
    return refs


def resolve_value(value: Any, ctx: RunContext) -> Any:
    """
    Resolve a single value (possibly nested). Refs are strings starting with @;
    logical_address = value[1:], looked up in ctx.bindings -> artifact_key -> store.get_any.
    """
    if isinstance(value, str):
        if value.startswith("@"):
            logical = value[1:]
            if logical not in ctx.bindings:
                raise KeyError(f"BindingNotFound: {logical}")
            artifact_key = ctx.bindings[logical]
            return ctx.store.get_any(artifact_key)
        return value
    if isinstance(value, list):
        return [resolve_value(item, ctx) for item in value]
    if isinstance(value, dict):
        return {k: resolve_value(v, ctx) for k, v in value.items()}
    return value


def collect_refs_in_inputs(inputs: dict[str, Any]) -> set[str]:
    """Collect all ref logical addresses present in step inputs (for validation)."""
    refs: set[str] = set()
    for v in inputs.values():
        refs |= _collect_refs(v)
    return refs
