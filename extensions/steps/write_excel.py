from __future__ import annotations

from flowbook.excel.io import write_df_to_excel


def op(inputs: dict, store_) -> dict:
    in_key: str = inputs["in_key"]

    df = store_.get_df(in_key)
    b = write_df_to_excel(df, sheet="out", index=False)
    return {"bytes": b}


def register(registry) -> None:
    registry.register("write_excel", op)
