# tests/test_apply_mapping_ops.py
import pandas as pd
import pytest

pytestmark = pytest.mark.unit

from flowbook.mapping.apply import apply_mapping_ops


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
