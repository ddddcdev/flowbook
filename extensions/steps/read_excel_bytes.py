from __future__ import annotations

from io import BytesIO

import pandas as pd


def op(inputs: dict, store_) -> dict:
    bytes_key: str = inputs["bytes_key"]
    sheet: str | int = inputs.get("sheet", 0)
    header: int = inputs.get("header", 0)
    out_key: str = inputs["out_key"]

    src = store_.get_bytes(bytes_key)
    df = pd.read_excel(BytesIO(src), engine="openpyxl", sheet_name=sheet, header=header)

    store_.put_df(out_key, df)
    return {"df": df}


def register(registry) -> None:
    registry.register("read_excel_bytes", op)
