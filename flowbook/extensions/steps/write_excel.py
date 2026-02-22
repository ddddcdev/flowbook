from __future__ import annotations

from typing import Any

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.excel.io import write_df_to_excel


@step("write_excel")
class WriteExcelOp(BaseOp):
    class Inputs(InputsBase):
        DF = "df"
        OUTPUT_FILENAME = "output_filename"
        REQUIRED = (DF,)
        OPTIONAL = (OUTPUT_FILENAME,)

    class Outputs(OutputsBase):
        BYTES = "bytes"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        df = inputs[self.Inputs.DF]
        b = write_df_to_excel(df, sheet="out", index=False)
        result: dict[str, Any] = {self.Outputs.BYTES: b}
        if output_filename := inputs.get(self.Inputs.OUTPUT_FILENAME):
            if isinstance(output_filename, str):
                result["_meta"] = {"filename": output_filename}
        return result


register = register_from_steps()
