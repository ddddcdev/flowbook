from __future__ import annotations

from typing import Any

from flowbook.excel.io import read_excel_table as read_excel_table_fn
from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.runtime.store import RunStore

KEY_PATH = "path"
KEY_SHEET = "sheet"
KEY_HEADER = "header"
KEY_REQUIRED_COLS = "required_cols"
KEY_OUT_KEY = "out_key"


class ReadExcelTableOp(BaseOp):
    required_inputs = (KEY_PATH, KEY_SHEET, KEY_REQUIRED_COLS, KEY_OUT_KEY)
    optional_inputs = (KEY_HEADER,)

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        path = inputs[KEY_PATH]
        sheet = inputs[KEY_SHEET]
        header = inputs.get(KEY_HEADER, 0)
        required_cols = inputs[KEY_REQUIRED_COLS]
        out_key = inputs[KEY_OUT_KEY]
        df = read_excel_table_fn(
            path,
            sheet=sheet,
            header=header,
            required_cols=required_cols,
        )
        store.put_df(out_key, df)
        return {"df": df}


def register(registry: Registry) -> None:
    registry.register("read_excel_table", ReadExcelTableOp())
