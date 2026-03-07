from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("read_excel_bytes")
class ReadExcelBytesOp(BaseOp):
    """Read Excel bytes into DataFrame. Uses openpyxl."""
    class Inputs(BaseInputs):
        src_excel_bytes: bytes
        sheet: int | str = 0
        header: int = 0

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        df = pd.read_excel(
            BytesIO(inp.src_excel_bytes),
            engine="openpyxl",
            sheet_name=inp.sheet,
            header=inp.header,
        )
        return self.Outputs(df=df).model_dump(mode="python")


register = register_from_steps()
