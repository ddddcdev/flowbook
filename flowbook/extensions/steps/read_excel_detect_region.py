"""
Detect table region by column hints, then read into DataFrame.

Excel table may start at any cell; other content may exist elsewhere (blank-separated).
Uses a pre-configured list of column names (hints) to find the header row and bounding box,
then extracts the table region. Designed for detail-style data with variable rows/columns.

Region detection is DataFrame-based and format-agnostic: the sheet is first read into a raw
DataFrame (engine selection handles .xlsx vs .xls), then region extraction operates on the
DataFrame only.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from flowbook.core.configs.spec_types import InputProfile
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.excel.io import excel_engine_from_filename, read_sheet_to_raw_df

# Limit scan to avoid reading huge sheets
DEFAULT_MAX_SCAN_ROWS = 500
DEFAULT_MAX_SCAN_COLS = 200


def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return s


def _row_values_from_df(df: pd.DataFrame, row_idx: int) -> list[tuple[int, str]]:
    """Return list of (col_0based, stripped_str) for non-empty cells in row."""
    out: list[tuple[int, str]] = []
    ncols = min(df.shape[1], DEFAULT_MAX_SCAN_COLS)
    for col_idx in range(ncols):
        s = _cell_str(df.iloc[row_idx, col_idx])
        if s:
            out.append((col_idx, s))
    return out


def _find_header_row_from_df(
    df: pd.DataFrame,
    column_hints: list[str],
    max_scan_rows: int = DEFAULT_MAX_SCAN_ROWS,
) -> tuple[int, dict[str, int]]:
    """
    Find first row that contains all column_hints (exact match after strip).
    Returns (header_row_0based, hint_to_col_0based).
    """
    hint_set = {h.strip() for h in column_hints if h.strip()}
    if not hint_set:
        raise ValueError("column_hints must contain at least one non-empty name")

    nrows = min(len(df), max_scan_rows)
    for row_idx in range(nrows):
        row_cells = _row_values_from_df(df, row_idx)
        values_in_row = {s for _, s in row_cells}
        if not (hint_set <= values_in_row):
            continue
        # Map each hint to its column (leftmost if duplicate)
        hint_to_col: dict[str, int] = {}
        for col_idx, s in row_cells:
            if s in hint_set and s not in hint_to_col:
                hint_to_col[s] = col_idx
        if set(hint_to_col.keys()) == hint_set:
            return (row_idx, hint_to_col)
    raise ValueError(
        f"No row found containing all column hints: {list(hint_set)}. "
        f"Scanned first {max_scan_rows} rows."
    )


def _extract_region_from_df(
    df: pd.DataFrame,
    header_row_0: int,
    hint_to_col_0: dict[str, int],
    column_hints: list[str],
) -> pd.DataFrame:
    """
    Extract table region: data rows from header_row+1 until a full blank row.
    Column order follows column_hints (left-to-right by col index).
    """
    # Header names in left-to-right order
    ordered = sorted(
        [(hint, hint_to_col_0[hint]) for hint in column_hints if hint.strip() in hint_to_col_0],
        key=lambda x: x[1],
    )
    col_names = [h for h, _ in ordered]
    col_indices = [hint_to_col_0[h] for h in col_names]

    rows_data: list[list[Any]] = []
    start = header_row_0 + 1
    end = min(header_row_0 + 1 + DEFAULT_MAX_SCAN_ROWS, len(df))
    for row_idx in range(start, end):
        row_vals = [df.iloc[row_idx, c] for c in col_indices]
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in row_vals):
            break
        values = [df.iloc[row_idx, c] for c in col_indices]
        rows_data.append(values)

    return pd.DataFrame(rows_data, columns=col_names)


@step("read_excel_detect_region")
class ReadExcelDetectRegionOp(BaseOp):
    """
    Find table region by configurable column hints (from InputProfile.column_hints),
    then extract that region as a DataFrame. Table may be anywhere; other content
    may exist in the sheet separated by blank rows/columns.

    Reads the sheet into a raw DataFrame first (engine from filename or default openpyxl),
    then performs region detection on the DataFrame. This separates format handling
    from region logic and supports both .xlsx and .xls.
    """

    class Inputs(InputsBase):
        SRC_EXCEL_BYTES = "src_excel_bytes"
        SRC_EXCEL_FILENAME = "src_excel_filename"
        SHEET = "sheet"
        REGION_PROFILE_NAME = "region_profile_name"
        OUTPUT_FILENAME = "output_filename"
        REQUIRED = (SRC_EXCEL_BYTES, REGION_PROFILE_NAME)
        OPTIONAL = (SRC_EXCEL_FILENAME, SHEET, OUTPUT_FILENAME)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        src = inputs[self.Inputs.SRC_EXCEL_BYTES]
        sheet = inputs.get(self.Inputs.SHEET, 0)
        profile_name = inputs[self.Inputs.REGION_PROFILE_NAME]
        src_filename = inputs.get(self.Inputs.SRC_EXCEL_FILENAME)

        profile = store.configs.get_spec(InputProfile, profile_name)
        column_hints = profile.get("column_hints")
        if not isinstance(column_hints, list) or not column_hints:
            raise ValueError(
                f"region_profile '{profile_name}' must have 'column_hints': list of column names"
            )
        column_hints = [str(h).strip() for h in column_hints if str(h).strip()]

        engine = excel_engine_from_filename(src_filename)
        raw_df = read_sheet_to_raw_df(src, sheet=sheet, engine=engine)

        header_row_0, hint_to_col_0 = _find_header_row_from_df(raw_df, column_hints)
        df = _extract_region_from_df(raw_df, header_row_0, hint_to_col_0, column_hints)

        result: dict[str, Any] = {self.Outputs.DF: df}
        if output_filename := inputs.get(self.Inputs.OUTPUT_FILENAME):
            if isinstance(output_filename, str):
                result["_meta"] = {"filename": output_filename}
        return result


register = register_from_steps()
