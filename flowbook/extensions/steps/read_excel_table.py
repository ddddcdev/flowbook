from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.excel.io import read_excel_table as read_excel_table_fn
from flowbook.extensions.steps._types import DataFrame


@step("read_excel_table")
class ReadExcelTableOp(BaseOp):
    """Read Excel sheet as table with header detection."""

    class Inputs(BaseInputs):
        path: str
        sheet: int | str
        required_cols: list[str]
        header: int = 0

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        df = read_excel_table_fn(
            inp.path,
            sheet=inp.sheet,
            header=inp.header,
            required_cols=inp.required_cols,
        )
        return self.Outputs(df=df).model_dump(mode="python")


register = register_from_steps()
