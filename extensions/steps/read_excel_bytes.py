from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.registry.spec import InputsBase, OutputsBase
from flowbook.runtime.store import RunStore


class ReadExcelBytesOp(BaseOp):
    class Inputs(InputsBase):
        BYTES_KEY = "bytes_key"
        OUT_KEY = "out_key"
        SHEET = "sheet"
        HEADER = "header"
        REQUIRED = (BYTES_KEY, OUT_KEY)
        OPTIONAL = (SHEET, HEADER)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        bytes_key = inputs[self.Inputs.BYTES_KEY]
        sheet = inputs.get(self.Inputs.SHEET, 0)
        header = inputs.get(self.Inputs.HEADER, 0)
        out_key = inputs[self.Inputs.OUT_KEY]

        src = store.get_bytes(bytes_key)
        df = pd.read_excel(BytesIO(src), engine="openpyxl", sheet_name=sheet, header=header)
        store.put_df(out_key, df)
        return {self.Outputs.DF: df}


def register(registry: Registry) -> None:
    registry.register("read_excel_bytes", ReadExcelBytesOp())
