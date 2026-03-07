from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.excel.io import write_df_to_excel
from flowbook.extensions.steps._types import DataFrame


@step("write_excel")
class WriteExcelOp(BaseOp):
    class Inputs(BaseInputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame
        output_filename: str | None = None

    class Outputs(BaseOutputs):
        bytes: bytes

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        result = self.Outputs(bytes=write_df_to_excel(inp.df, sheet="out", index=False)).model_dump(
            mode="python"
        )
        if inp.output_filename:
            result["_meta"] = {"filename": inp.output_filename}
        return result


register = register_from_steps()
