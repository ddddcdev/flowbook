# tests/test_apply_mapping_ops.py
import pandas as pd
import pytest

from flowbook.extensions.excel.mapping.apply import apply_mapping_ops

pytestmark = pytest.mark.unit


def test_apply_mapping_ops_select_rename_filter():
    df = pd.DataFrame({"a": [1, -1, 2], "b": [10, 20, 30], "x": [9, 9, 9]})
    ops = [
        {"op": "select_cols", "cols": ["a", "b"]},
        {"op": "rename", "map": {"a": "A"}},
        {"op": "filter_rows", "expr": "A > 0"},
    ]
    out = apply_mapping_ops(df, ops)
    assert list(out.columns) == ["A", "b"]
    assert out["A"].tolist() == [1, 2]
    assert out["b"].tolist() == [10, 30]


def test_apply_mapping_ops_filter_rows_and_or():
    """filter_rows with engine=python supports & and |."""
    df = pd.DataFrame({"p": [1, 0, 1, 0], "q": [0, 1, 1, 0]})
    ops = [{"op": "filter_rows", "expr": "(p == 1) & (q == 1)"}]
    out = apply_mapping_ops(df, ops)
    assert len(out) == 1
    assert out.iloc[0]["p"] == 1 and out.iloc[0]["q"] == 1


def test_apply_mapping_ops_expr_df():
    """expr_df adds new columns from expressions."""
    df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
    ops = [
        {"op": "expr_df", "columns": [{"name": "sum_ab", "expr": "a + b"}]},
        {"op": "expr_df", "columns": [{"name": "double_a", "expr": "a * 2"}]},
    ]
    out = apply_mapping_ops(df, ops)
    assert list(out.columns) == ["a", "b", "sum_ab", "double_a"]
    assert out["sum_ab"].tolist() == [11, 22, 33]
    assert out["double_a"].tolist() == [2, 4, 6]
