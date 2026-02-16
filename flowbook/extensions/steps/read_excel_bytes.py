from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("read_excel_bytes")
class ReadExcelBytesOp(BaseOp):
    class Inputs(InputsBase):
        SRC_EXCEL_BYTES = "src_excel_bytes"
        SHEET = "sheet"
        HEADER = "header"
        REQUIRED = (SRC_EXCEL_BYTES,)
        OPTIONAL = (SHEET, HEADER)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        src = inputs[self.Inputs.SRC_EXCEL_BYTES]
        sheet = inputs.get(self.Inputs.SHEET, 0)
        header = inputs.get(self.Inputs.HEADER, 0)

        df = pd.read_excel(BytesIO(src), engine="openpyxl", sheet_name=sheet, header=header)
        return {self.Outputs.DF: df}


register = register_from_steps()
