"""Tests for run-level warning aggregation from step _warnings output."""

from __future__ import annotations

from typing import Any

import pytest

from flowbook import (
    DefaultRunStore,
    InMemoryArtifactsStore,
    InMemoryConfigStore,
    Registry,
)
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.runtime.build import build
from flowbook.core.runtime.context import RunContext
from flowbook.core.runtime.executor import execute_plan

pytestmark = pytest.mark.unit


class _WarnOp(BaseOp):
    """One-off op that returns _warnings for testing."""

    class Inputs(InputsBase):
        REQUIRED = ()
        OPTIONAL = ()

    class Outputs(OutputsBase):
        OUT = "out"

    def __call__(self, inputs: dict[str, Any], store: Any) -> dict[str, Any]:
        return {self.Outputs.OUT: 42, "_warnings": ["warning one", "warning two"]}


def test_run_aggregates_step_warnings_into_run_info() -> None:
    """A step that returns _warnings has them aggregated in RunInfo.warnings."""
    artifacts = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    store = DefaultRunStore(artifacts=artifacts, configs=config_store)
    registry = Registry()
    registry.register("warn_op", _WarnOp())

    plan_config = {
        "steps": [
            {"name": "w", "op": "warn_op", "inputs": {}},
        ]
    }
    plan = build(plan_config)
    ctx = RunContext(
        run_id="r1",
        entity_key="default",
        store=store,
        registry=registry,
        bindings={},
    )

    info = execute_plan(plan, ctx)

    assert info.status == "succeeded"
    assert info.warnings == ["warning one", "warning two"]
    # _warnings must not be persisted as artifact
    assert "r1/default/w/out" in info.artifacts_written
    assert not any("_warnings" in k for k in info.artifacts_written)
