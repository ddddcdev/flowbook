from __future__ import annotations

from flowbook.excel.io import read_excel_to_df


def op(inputs: dict, store_) -> dict:
    path: str = inputs["path"]
    sheet: str | int = inputs.get("sheet", 0)
    header: int = inputs.get("header", 0)
    out_key: str = inputs["out_key"]

    df = read_excel_to_df(path, sheet=sheet, header=header)
    store_.put_df(out_key, df)
    return {"out_key": out_key}


def register(registry) -> None:
    registry.register("read_excel", op)
