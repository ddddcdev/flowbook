from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.runtime.store import RunStore

KEY_BYTES_KEY = "bytes_key"
KEY_OUT_KEY = "out_key"
KEY_SHEET = "sheet"
KEY_HEADER = "header"


class ReadExcelBytesOp(BaseOp):
    required_inputs = (KEY_BYTES_KEY, KEY_OUT_KEY)
    optional_inputs = (KEY_SHEET, KEY_HEADER)

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        bytes_key: str = inputs[KEY_BYTES_KEY]
        sheet: str | int = inputs.get(KEY_SHEET, 0)
        header: int = inputs.get(KEY_HEADER, 0)
        out_key: str = inputs[KEY_OUT_KEY]

        src = store.get_bytes(bytes_key)
        df = pd.read_excel(BytesIO(src), engine="openpyxl", sheet_name=sheet, header=header)
        store.put_df(out_key, df)
        return {"df": df}


def register(registry: Registry) -> None:
    registry.register("read_excel_bytes", ReadExcelBytesOp())
