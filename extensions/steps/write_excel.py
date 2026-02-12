from __future__ import annotations

from typing import Any

from flowbook.excel.io import write_df_to_excel
from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.registry.spec import InputsBase, OutputsBase
from flowbook.runtime.store import RunStore


class WriteExcelOp(BaseOp):
    class Inputs(InputsBase):
        DF = "df"
        REQUIRED = (DF,)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        BYTES = "bytes"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        df = inputs[self.Inputs.DF]
        b = write_df_to_excel(df, sheet="out", index=False)
        return {self.Outputs.BYTES: b}


def register(registry: Registry) -> None:
    registry.register("write_excel", WriteExcelOp())
