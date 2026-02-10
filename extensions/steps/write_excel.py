from __future__ import annotations

from flowbook.excel.io import write_df_to_excel
from flowbook.registry.base_op import BaseOp


KEY_IN_KEY = "in_key"


class WriteExcelOp(BaseOp):
    required_inputs = (KEY_IN_KEY,)
    optional_inputs = ()

    def __call__(self, inputs: dict, store_) -> dict:
        in_key: str = inputs[KEY_IN_KEY]
        df = store_.get_df(in_key)
        b = write_df_to_excel(df, sheet="out", index=False)
        return {"bytes": b}


def register(registry) -> None:
    registry.register("write_excel", WriteExcelOp())
