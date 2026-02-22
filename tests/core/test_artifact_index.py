"""Unit tests for artifact index (InMemory, run recording)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from flowbook import (
    DefaultRunStore,
    InMemoryArtifactIndex,
    InMemoryArtifactsStore,
    InMemoryConfigStore,
    Registry,
    register_steps,
)
from flowbook.core.runtime.build import build
from flowbook.core.runtime.context import RunContext
from flowbook.core.runtime.run import run

pytestmark = pytest.mark.unit


def test_in_memory_index_record_list_and_latest() -> None:
    idx = InMemoryArtifactIndex()
    base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    idx.record("r1", "r1/u1/s1/df", "s1/df", "u1", base, "application/vnd.dataframe")
    idx.record("r1", "r1/u2/s2/df", "s2/df", "u2", base, "application/json")
    later = datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    idx.record("r2", "r2/u1/s1/df", "s1/df", "u1", later, "application/json")

    list_u1 = idx.list_index("u1", limit=10, order="desc")
    assert len(list_u1) == 2
    assert list_u1[0].artifact_key == "r2/u1/s1/df"
    assert list_u1[1].artifact_key == "r1/u1/s1/df"

    latest = idx.latest_per_logical("u1", limit=10)
    assert len(latest) == 1
    assert latest[0].logical_address == "s1/df"
    assert latest[0].artifact_key == "r2/u1/s1/df"


def test_run_with_index_records_outputs() -> None:
    store = DefaultRunStore(artifacts=InMemoryArtifactsStore(), configs=InMemoryConfigStore())
    registry = Registry()
    register_steps(registry)
    index = InMemoryArtifactIndex()
    ctx = RunContext(
        run_id="run1",
        entity_key="add",
        store=store,
        registry=registry,
        bindings={},
        index=index,
    )
    plan = build(
        {
            "steps": [
                {"name": "add", "op": "add", "inputs": {"x": "@x", "y": "@y"}},
            ]
        }
    )
    ctx.bindings["x"] = "run1//input/x"
    ctx.bindings["y"] = "run1//input/y"
    store.put("run1//input/x", 2)
    store.put("run1//input/y", 3)

    info = run(plan, ctx)

    assert info.status == "succeeded"
    rows = index.list_index("add", limit=10)
    assert len(rows) == 1
    assert rows[0].logical_address == "add/sum"
    assert rows[0].artifact_key == "run1/add/add/sum"
    assert rows[0].entity_key == "add"
