from __future__ import annotations

from typing import Any

from flowbook.excel.io import read_excel_to_df
from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.runtime.store import RunStore

KEY_PATH = "path"
KEY_SHEET = "sheet"
KEY_HEADER = "header"
KEY_OUT_KEY = "out_key"


class ReadExcelOp(BaseOp):
    required_inputs = (KEY_PATH, KEY_OUT_KEY)
    optional_inputs = (KEY_SHEET, KEY_HEADER)

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        path = inputs[KEY_PATH]
        sheet = inputs.get(KEY_SHEET, 0)
        header = inputs.get(KEY_HEADER, 0)
        out_key = inputs[KEY_OUT_KEY]
        df = read_excel_to_df(path, sheet=sheet, header=header)
        store.put_df(out_key, df)
        return {"df": df}


def register(registry: Registry) -> None:
    registry.register("read_excel", ReadExcelOp())
