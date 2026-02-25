from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from flowbook.extensions.excel.errors import MissingRequiredColumnsError


def excel_engine_from_filename(filename: str | None) -> str:
    """
    Infer pandas read_excel engine from file extension.
    Returns 'xlrd' for .xls, 'openpyxl' for .xlsx/.xlsm, else 'openpyxl'.
    """
    if not filename:
        return "openpyxl"
    lower = filename.lower()
    if lower.endswith(".xls") and not (lower.endswith(".xlsx") or lower.endswith(".xlsm")):
        return "xlrd"
    return "openpyxl"


def read_sheet_to_raw_df(
    source: str | Path | bytes,
    sheet: str | int = 0,
    engine: str | None = "openpyxl",
) -> pd.DataFrame:
    """
    Read entire sheet as raw DataFrame (header=None).
    Use for format-agnostic region detection; engine selection is separate.
    """
    if isinstance(source, bytes):
        io_obj: Path | io.BytesIO = io.BytesIO(source)
    else:
        io_obj = Path(source)
    return pd.read_excel(io_obj, sheet_name=sheet, header=None, engine=engine)


def read_excel_to_df(
    path: str | Path,
    sheet: str | int = 0,
    header: int = 0,
    dtype: dict[str, Any] | None = None,
    engine: str | None = "openpyxl",
) -> pd.DataFrame:
    kwargs: dict[str, Any] = {
        "sheet_name": sheet,
        "header": header,
    }
    if dtype is not None:
        kwargs["dtype"] = dtype
    if engine is not None:
        kwargs["engine"] = engine
    return pd.read_excel(Path(path), **kwargs)


def write_df_to_excel(
    df: pd.DataFrame,
    sheet: str = "out",
    index: bool = False,
    engine: Literal["openpyxl", "odf", "xlsxwriter", "auto"] | None = "openpyxl",
) -> bytes:
    import io

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine=engine) as writer:
        df.to_excel(writer, sheet_name=sheet, index=index)
    return buf.getvalue()


def read_excel_table(
    path: str | Path,
    sheet: str | int,
    header: int,
    required_cols: list[str],
    dtype: dict[str, Any] | None = None,
    engine: str | None = "openpyxl",
) -> pd.DataFrame:
    df = read_excel_to_df(path=path, sheet=sheet, header=header, dtype=dtype, engine=engine)

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise MissingRequiredColumnsError(missing)

    return df
