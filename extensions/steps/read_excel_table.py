from __future__ import annotations

from flowbook.excel.io import read_excel_table


def op(inputs: dict, store_) -> dict:
    path: str = inputs["path"]
    sheet: str | int = inputs["sheet"]
    header: int = inputs.get("header", 0)
    required_cols: list[str] = inputs["required_cols"]
    out_key: str = inputs["out_key"]

    df = read_excel_table(
        path,
        sheet=sheet,
        header=header,
        required_cols=required_cols,
    )
    store_.put_df(out_key, df)
    return {"df": df}


def register(registry) -> None:
    registry.register("read_excel_table", op)
