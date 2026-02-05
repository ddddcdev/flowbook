from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd

from .errors import MissingRequiredColumnsError


def read_excel_to_df(
    path: str | Path,
    sheet: str | int = 0,
    header: int = 0,  # 0-based
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
    # pandas は engine を ExcelWriter で見る。ここでは openpyxl を暗黙利用
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
