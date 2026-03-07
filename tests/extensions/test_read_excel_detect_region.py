"""
Unit tests for read_excel_detect_region step (df-based region extraction).
"""

from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import pandas as pd
import pytest

from flowbook import (
    Engine,
    InMemoryArtifactsStore,
    InMemoryConfigStore,
    Registry,
    register_steps,
)
from flowbook.core.configs.spec_types import InputProfile
from flowbook.extensions.excel.io import excel_engine_from_filename, read_sheet_to_raw_df
from flowbook.extensions.steps.read_excel_detect_region import (
    ReadExcelDetectRegionOp,
    _extract_region_from_df,
    _find_header_row_from_df,
)

pytestmark = pytest.mark.unit


def _make_detect_region_xlsx() -> bytes:
    """Create xlsx with table at B6:H10 (header row 6)."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_raw = pd.DataFrame(
            [
                [None, None, None, None, "Other table", None, None, None],
                [None, None, None, None, None, None, None, None],
                [None, None, None, None, None, None, None, None],
                [None, None, None, None, None, None, None, None],
                [None, None, None, None, None, None, None, None],
                [None, "LineNo", "Item", "Qty", "Extra1", "Extra2", "Note", "Date"],
                [None, 1, "a", 10, "x", 100, "memo1", "2025-01-15"],
                [None, 2, "b", 20, None, 200, None, "2024-12-01"],
                [None, 3, "c", 30, "z", 300, "memo3", "2025-02-01"],
                [None, 4, "d", 40, None, None, "", "2024-06-01"],
                [None, None, None, None, None, None, None, None],
            ]
        )
        df_raw.to_excel(w, sheet_name="data", index=False, header=False, startrow=0)
    return buf.getvalue()


def test_excel_engine_from_filename() -> None:
    assert excel_engine_from_filename(None) == "openpyxl"
    assert excel_engine_from_filename("") == "openpyxl"
    assert excel_engine_from_filename("file.xlsx") == "openpyxl"
    assert excel_engine_from_filename("file.XLSX") == "openpyxl"
    assert excel_engine_from_filename("file.xls") == "xlrd"
    assert excel_engine_from_filename("file.XLS") == "xlrd"
    assert excel_engine_from_filename("file.xlsm") == "openpyxl"


def test_read_sheet_to_raw_df() -> None:
    xlsx = _make_detect_region_xlsx()
    df = read_sheet_to_raw_df(xlsx, sheet=0, engine="openpyxl")
    assert df.shape[0] >= 10
    assert df.shape[1] >= 8


def test_find_header_row_from_df() -> None:
    xlsx = _make_detect_region_xlsx()
    df = read_sheet_to_raw_df(xlsx, sheet=0, engine="openpyxl")
    hints = ["LineNo", "Item", "Qty", "Note", "Date"]
    row_0, hint_to_col = _find_header_row_from_df(df, hints)
    assert row_0 == 5
    assert hint_to_col["LineNo"] == 1
    assert hint_to_col["Item"] == 2
    assert hint_to_col["Qty"] == 3


def test_extract_region_from_df() -> None:
    xlsx = _make_detect_region_xlsx()
    df = read_sheet_to_raw_df(xlsx, sheet=0, engine="openpyxl")
    hints = ["LineNo", "Item", "Qty", "Note", "Date"]
    row_0, hint_to_col = _find_header_row_from_df(df, hints)
    out = _extract_region_from_df(df, row_0, hint_to_col, hints)
    assert list(out.columns) == ["LineNo", "Item", "Qty", "Note", "Date"]
    assert len(out) == 4
    assert out.iloc[0]["LineNo"] == 1
    assert out.iloc[0]["Item"] == "a"
    assert out.iloc[0]["Qty"] == 10


def test_read_excel_detect_region_op() -> None:
    store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    config_store.put_spec(
        InputProfile,
        "detail_region",
        {
            "kind_rules": [],
            "column_hints": ["LineNo", "Item", "Qty", "Extra1", "Extra2", "Note", "Date"],
        },
        config_id=str(uuid4()),
    )

    registry = Registry()
    register_steps(registry)
    engine = Engine(
        store=store,
        registry=registry,
        config_store=config_store,
        meta={"env": "test"},
    )

    xlsx = _make_detect_region_xlsx()
    op = ReadExcelDetectRegionOp()

    with engine.create_run() as run:
        result = op(
            {
                "src_excel_bytes": xlsx,
                "src_excel_filename": "test.xlsx",
                "sheet": "data",
                "region_profile_name": "detail_region",
            },
            run.store,
        )

    df = result["df"]
    assert list(df.columns) == ["LineNo", "Item", "Qty", "Extra1", "Extra2", "Note", "Date"]
    assert len(df) == 4
    assert df.iloc[2]["Item"] == "c"
    assert df.iloc[2]["Qty"] == 30


def test_read_excel_detect_region_op_without_filename() -> None:
    """Without src_excel_filename, defaults to openpyxl (backward compat for .xlsx)."""
    store = InMemoryArtifactsStore()
    config_store = InMemoryConfigStore()
    config_store.put_spec(
        InputProfile,
        "detail_region",
        {"kind_rules": [], "column_hints": ["LineNo", "Item", "Qty"]},
        config_id=str(uuid4()),
    )

    registry = Registry()
    register_steps(registry)
    engine = Engine(
        store=store,
        registry=registry,
        config_store=config_store,
        meta={"env": "test"},
    )

    xlsx = _make_detect_region_xlsx()
    op = ReadExcelDetectRegionOp()

    with engine.create_run() as run:
        result = op(
            {
                "src_excel_bytes": xlsx,
                "sheet": "data",
                "region_profile_name": "detail_region",
            },
            run.store,
        )

    df = result["df"]
    assert list(df.columns) == ["LineNo", "Item", "Qty"]
    assert len(df) == 4
