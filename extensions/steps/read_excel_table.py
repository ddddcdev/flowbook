from __future__ import annotations

from typing import Any

from flowbook.excel.io import read_excel_table as read_excel_table_fn
from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.registry.spec import InputsBase, OutputsBase
from flowbook.runtime.store import RunStore


class ReadExcelTableOp(BaseOp):
    class Inputs(InputsBase):
        PATH = "path"
        SHEET = "sheet"
        HEADER = "header"
        REQUIRED_COLS = "required_cols"
        REQUIRED = (PATH, SHEET, REQUIRED_COLS)
        OPTIONAL = (HEADER,)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        path = inputs[self.Inputs.PATH]
        sheet = inputs[self.Inputs.SHEET]
        header = inputs.get(self.Inputs.HEADER, 0)
        required_cols = inputs[self.Inputs.REQUIRED_COLS]
        df = read_excel_table_fn(
            path,
            sheet=sheet,
            header=header,
            required_cols=required_cols,
        )
        return {self.Outputs.DF: df}


def register(registry: Registry) -> None:
    registry.register("read_excel_table", ReadExcelTableOp())
