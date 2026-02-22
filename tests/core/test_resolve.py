"""Unit tests for ref resolution: resolve_value, collect_refs_in_inputs."""

from __future__ import annotations

from typing import Any

import pytest

from flowbook.core.configs.null_store import NullConfigStore
from flowbook.core.runtime.context import RunContext
from flowbook.core.runtime.resolve import collect_refs_in_inputs, resolve_value
from flowbook.core.runtime.store import RunStore


class _MockStore:
    """Minimal store for resolver tests: get_any + configs."""

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data
        self.configs = NullConfigStore()

    def get_any(self, key: str) -> object:
        if key not in self._data:
            raise KeyError(key)
        return self._data[key]


def _ctx(bindings: dict[str, str], store_data: dict[str, Any] | None = None) -> RunContext:
    data = store_data if store_data is not None else {k: f"val_{k}" for k in bindings.values()}
    store: RunStore = _MockStore(data)  # type: ignore[assignment]
    from flowbook.core.registry.registry import Registry

    return RunContext(
        run_id="run1",
        entity_key="default",
        store=store,
        registry=Registry(),
        bindings=bindings,
    )


pytestmark = pytest.mark.unit


def test_resolve_ref_opaque_key() -> None:
    """@a/b/c resolves as opaque logical address via bindings."""
    bindings = {"a/b/c": "run1/step/out"}
    store_data = {"run1/step/out": 42}
    ctx = _ctx(bindings, store_data)
    assert resolve_value("@a/b/c", ctx) == 42


def test_resolve_literal_unchanged() -> None:
    """Strings not starting with @ are returned as-is."""
    ctx = _ctx({"x": "k"})
    assert resolve_value("hello", ctx) == "hello"
    assert resolve_value("read/df", ctx) == "read/df"
    assert resolve_value("", ctx) == ""


def test_resolve_list_of_refs() -> None:
    """List of refs resolves each element."""
    bindings = {"a/df": "k1", "b/df": "k2"}
    store_data = {"k1": "df_a", "k2": "df_b"}
    ctx = _ctx(bindings, store_data)
    out = resolve_value(["@a/df", "@b/df"], ctx)
    assert out == ["df_a", "df_b"]


def test_resolve_dict_mixed_literals_refs() -> None:
    """Dict with mixed literals and refs resolves only ref values."""
    bindings = {"load/df": "key_df"}
    store_data = {"key_df": "resolved_df"}
    ctx = _ctx(bindings, store_data)
    raw = {"left": "@load/df", "how": "left", "on": ["id"]}
    out = resolve_value(raw, ctx)
    assert out == {"left": "resolved_df", "how": "left", "on": ["id"]}


def test_resolve_non_string_non_collection_unchanged() -> None:
    """Numbers, bools, None are returned as-is."""
    ctx = _ctx({})
    assert resolve_value(1, ctx) == 1
    assert resolve_value(3.14, ctx) == 3.14
    assert resolve_value(True, ctx) is True
    assert resolve_value(None, ctx) is None


def test_collect_refs_in_inputs() -> None:
    """collect_refs_in_inputs gathers all @ ref logical addresses."""
    inputs = {"left": "@a/df", "right": "@b/df", "how": "left", "dfs": ["@x/df", "@y/df"]}
    refs = collect_refs_in_inputs(inputs)
    assert refs == {"a/df", "b/df", "x/df", "y/df"}


def test_collect_refs_no_refs() -> None:
    """No refs returns empty set."""
    assert collect_refs_in_inputs({"a": "literal", "b": 1}) == set()


def test_resolve_ref_missing_binding_raises() -> None:
    """Ref with logical address not in bindings raises KeyError."""
    ctx = _ctx({"other": "k"})
    with pytest.raises(KeyError, match="BindingNotFound: missing/key"):
        resolve_value("@missing/key", ctx)
