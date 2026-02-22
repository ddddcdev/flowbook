"""Unit tests for generic DataFrame step ops: merge_df, aggregate_df, concat_df, check_warn."""

from __future__ import annotations

import pandas as pd
import pytest

from flowbook import (
    DefaultRunStore,
    InMemoryArtifactsStore,
    InMemoryConfigStore,
    Registry,
    register_steps,
)
from flowbook.core.runtime.build import build
from flowbook.core.runtime.context import RunContext
from flowbook.core.runtime.run import run
from flowbook.extensions.steps.aggregate_df import AggregateDfOp
from flowbook.extensions.steps.concat_df import ConcatDfOp
from flowbook.extensions.steps.merge_df import MergeDfOp

pytestmark = pytest.mark.unit


def _store_and_ctx(
    bindings: dict[str, str], store_data: dict[str, pd.DataFrame]
) -> tuple[DefaultRunStore, RunContext]:
    artifacts = InMemoryArtifactsStore()
    for k, v in store_data.items():
        artifacts.put_df(k, v)
    config_store = InMemoryConfigStore()
    store = DefaultRunStore(artifacts=artifacts, configs=config_store)
    registry = Registry()
    register_steps(registry)
    return store, RunContext(
        run_id="r1",
        entity_key="default",
        store=store,
        registry=registry,
        bindings=bindings,
    )


def test_merge_df() -> None:
    left = pd.DataFrame({"id": [1, 2], "a": [10, 20]})
    right = pd.DataFrame({"id": [1, 3], "b": [100, 300]})
    store_data = {"k_left": left, "k_right": right}
    bindings = {"load_left/df": "k_left", "load_right/df": "k_right"}
    store, ctx = _store_and_ctx(bindings, store_data)
    pipeline = build(
        {
            "steps": [
                {
                    "name": "join",
                    "op": "merge_df",
                    "inputs": {
                        "left": "@load_left/df",
                        "right": "@load_right/df",
                        "on": "id",
                        "how": "inner",
                    },
                }
            ]
        }
    )
    info = run(pipeline, ctx)
    assert info.status == "succeeded"
    out_key = info.steps[0].outputs[MergeDfOp.Outputs.DF]
    out = store.get_df(out_key)
    assert list(out.columns) == ["id", "a", "b"]
    assert out["id"].tolist() == [1]
    assert out["a"].tolist() == [10]
    assert out["b"].tolist() == [100]


def test_aggregate_df() -> None:
    df = pd.DataFrame({"g": ["x", "x", "y"], "v": [1, 2, 3]})
    bindings = {"src/df": "k_src"}
    store_data = {"k_src": df}
    store, ctx = _store_and_ctx(bindings, store_data)
    pipeline = build(
        {
            "steps": [
                {
                    "name": "agg",
                    "op": "aggregate_df",
                    "inputs": {"df": "@src/df", "group_by": ["g"], "agg": {"v": "sum"}},
                }
            ]
        }
    )
    info = run(pipeline, ctx)
    assert info.status == "succeeded"
    out_key = info.steps[0].outputs[AggregateDfOp.Outputs.DF]
    out = store.get_df(out_key)
    assert out["g"].tolist() == ["x", "y"]
    assert out["v"].tolist() == [3, 3]


def test_concat_df() -> None:
    a = pd.DataFrame({"x": [1, 2]})
    b = pd.DataFrame({"x": [3, 4]})
    bindings = {"a/df": "k_a", "b/df": "k_b"}
    store_data = {"k_a": a, "k_b": b}
    store, ctx = _store_and_ctx(bindings, store_data)
    pipeline = build(
        {
            "steps": [
                {
                    "name": "stack",
                    "op": "concat_df",
                    "inputs": {"dfs": ["@a/df", "@b/df"], "ignore_index": True},
                }
            ]
        }
    )
    info = run(pipeline, ctx)
    assert info.status == "succeeded"
    out_key = info.steps[0].outputs[ConcatDfOp.Outputs.DF]
    out = store.get_df(out_key)
    assert out["x"].tolist() == [1, 2, 3, 4]


def test_check_warn_aggregates_warnings() -> None:
    df = pd.DataFrame({"a": [1, 2, 0], "b": [10, 20, 30]})
    bindings = {"main/df": "k_main"}
    store_data = {"k_main": df}
    store, ctx = _store_and_ctx(bindings, store_data)
    pipeline = build(
        {
            "steps": [
                {
                    "name": "chk",
                    "op": "check_warn",
                    "inputs": {
                        "df": "@main/df",
                        "checks": [
                            {"expr": "a == 0", "message": "found zero in a"},
                            {"expr": "b > 25", "message": "b too high"},
                        ],
                    },
                }
            ]
        }
    )
    info = run(pipeline, ctx)
    assert info.status == "succeeded"
    assert "found zero in a" in info.warnings
    assert "b too high" in info.warnings
