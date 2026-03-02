from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("read_csv_bytes")
class ReadCsvBytesOp(BaseOp):
    """Read CSV bytes into a DataFrame."""

    class Inputs(InputsBase):
        SRC_CSV_BYTES = "src_csv_bytes"
        ENCODING = "encoding"
        HEADER = "header"
        REQUIRED = (SRC_CSV_BYTES,)
        OPTIONAL = (ENCODING, HEADER)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        src = inputs[self.Inputs.SRC_CSV_BYTES]
        encoding = inputs.get(self.Inputs.ENCODING, "utf-8")
        header = inputs.get(self.Inputs.HEADER, 0)

        df = pd.read_csv(BytesIO(src), encoding=encoding, header=header)
        return {self.Outputs.DF: df}


register = register_from_steps()
