"""
Detect table region by column hints, then read into DataFrame.

Excel table may start at any cell; other content may exist elsewhere (blank-separated).
Uses a pre-configured list of column names (hints) to find the header row and bounding box,
then extracts the table region. Designed for detail-style data with variable rows/columns.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import openpyxl
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from flowbook.core.configs.spec_types import InputProfile
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore

# Limit scan to avoid reading huge sheets
DEFAULT_MAX_SCAN_ROWS = 500
DEFAULT_MAX_SCAN_COLS = 200


def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return s


def _row_values_1based(ws: Worksheet, row_1: int) -> list[tuple[int, str]]:
    """Return list of (col_1based, stripped_str) for non-empty cells in row."""
    out: list[tuple[int, str]] = []
    for col_1 in range(1, DEFAULT_MAX_SCAN_COLS + 1):
        cell = ws.cell(row=row_1, column=col_1)
        s = _cell_str(cell.value)
        if s:
            out.append((col_1, s))
    return out


def _find_header_row(
    ws: Worksheet,
    column_hints: list[str],
    max_scan_rows: int = DEFAULT_MAX_SCAN_ROWS,
) -> tuple[int, dict[str, int]]:
    """
    Find first row that contains all column_hints (exact match after strip).
    Returns (header_row_1based, hint_to_col_1based).
    """
    hint_set = {h.strip() for h in column_hints if h.strip()}
    if not hint_set:
        raise ValueError("column_hints must contain at least one non-empty name")

    for row_1 in range(1, max_scan_rows + 1):
        row_cells = _row_values_1based(ws, row_1)
        values_in_row = {s for _, s in row_cells}
        if not (hint_set <= values_in_row):
            continue
        # Map each hint to its column (leftmost if duplicate)
        hint_to_col: dict[str, int] = {}
        for col_1, s in row_cells:
            if s in hint_set and s not in hint_to_col:
                hint_to_col[s] = col_1
        if set(hint_to_col.keys()) == hint_set:
            return (row_1, hint_to_col)
    raise ValueError(
        f"No row found containing all column hints: {list(hint_set)}. "
        f"Scanned first {max_scan_rows} rows."
    )


def _read_region(
    ws: Worksheet,
    header_row_1: int,
    hint_to_col_1: dict[str, int],
    column_hints: list[str],
) -> pd.DataFrame:
    """
    Read table region: header row and data rows until a full blank row.
    Column order follows column_hints (left-to-right by col index).
    """
    min_col = min(hint_to_col_1.values())
    max_col = max(hint_to_col_1.values())
    # Header names in left-to-right order
    ordered = sorted(
        [(hint, hint_to_col_1[hint]) for hint in column_hints if hint.strip() in hint_to_col_1],
        key=lambda x: x[1],
    )
    col_names = [h for h, _ in ordered]

    rows_data: list[list[Any]] = []
    for row_1 in range(header_row_1 + 1, header_row_1 + 1 + DEFAULT_MAX_SCAN_ROWS):
        row_vals = [ws.cell(row=row_1, column=c).value for c in range(min_col, max_col + 1)]
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in row_vals):
            break
        # Map to columns by header order
        values = [ws.cell(row=row_1, column=hint_to_col_1[name]).value for name in col_names]
        rows_data.append(values)

    return pd.DataFrame(rows_data, columns=col_names)


@step("read_excel_detect_region")
class ReadExcelDetectRegionOp(BaseOp):
    """
    Find table region by configurable column hints (from InputProfile.column_hints),
    then extract that region as a DataFrame. Table may be anywhere; other content
    may exist in the sheet separated by blank rows/columns.
    """

    class Inputs(InputsBase):
        SRC_EXCEL_BYTES = "src_excel_bytes"
        SHEET = "sheet"
        REGION_PROFILE_NAME = "region_profile_name"
        OUTPUT_FILENAME = "output_filename"
        REQUIRED = (SRC_EXCEL_BYTES, REGION_PROFILE_NAME)
        OPTIONAL = (SHEET, OUTPUT_FILENAME)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        src = inputs[self.Inputs.SRC_EXCEL_BYTES]
        sheet = inputs.get(self.Inputs.SHEET, 0)
        profile_name = inputs[self.Inputs.REGION_PROFILE_NAME]

        profile = store.configs.get_spec(InputProfile, profile_name)
        column_hints = profile.get("column_hints")
        if not isinstance(column_hints, list) or not column_hints:
            raise ValueError(
                f"region_profile '{profile_name}' must have 'column_hints': list of column names"
            )
        column_hints = [str(h).strip() for h in column_hints if str(h).strip()]

        wb = openpyxl.load_workbook(BytesIO(src), data_only=True, read_only=False)
        if isinstance(sheet, int):
            ws = wb.worksheets[sheet]
        else:
            ws = wb[sheet]

        header_row_1, hint_to_col_1 = _find_header_row(ws, column_hints)
        df = _read_region(ws, header_row_1, hint_to_col_1, column_hints)

        result: dict[str, Any] = {self.Outputs.DF: df}
        if output_filename := inputs.get(self.Inputs.OUTPUT_FILENAME):
            if isinstance(output_filename, str):
                result["_meta"] = {"filename": output_filename}
        return result


register = register_from_steps()
