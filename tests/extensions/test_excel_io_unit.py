from __future__ import annotations

import pandas as pd
import pytest

from flowbook.extensions.excel.errors import MissingRequiredColumnsError
from flowbook.extensions.excel.io import read_excel_table, write_df_to_excel

pytestmark = pytest.mark.unit


def test_write_df_to_excel_bytes_readable(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    b = write_df_to_excel(df, sheet="out", index=False)
    p = tmp_path / "out.xlsx"
    p.write_bytes(b)

    df2 = pd.read_excel(p, sheet_name="out", engine="openpyxl")
    assert list(df2.columns) == ["a", "b"]
    assert len(df2) == 2


def test_read_excel_table_missing_required_cols_raises(tmp_path):
    df = pd.DataFrame({"a": [1]})
    p = tmp_path / "in.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="in", index=False)

    try:
        read_excel_table(path=p, sheet="in", header=0, required_cols=["a", "b"])
        raise AssertionError("expected MissingRequiredColumnsError")
    except MissingRequiredColumnsError as e:
        assert e.missing == ["b"]
