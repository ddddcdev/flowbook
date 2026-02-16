from __future__ import annotations

from typing import Any

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.excel.io import read_excel_to_df


@step("read_excel")
class ReadExcelOp(BaseOp):
    class Inputs(InputsBase):
        PATH = "path"
        SHEET = "sheet"
        HEADER = "header"
        REQUIRED = (PATH,)
        OPTIONAL = (SHEET, HEADER)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        path = inputs[self.Inputs.PATH]
        sheet = inputs.get(self.Inputs.SHEET, 0)
        header = inputs.get(self.Inputs.HEADER, 0)
        df = read_excel_to_df(path, sheet=sheet, header=header)
        return {self.Outputs.DF: df}


register = register_from_steps()
