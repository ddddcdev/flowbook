from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("read_csv_bytes")
class ReadCsvBytesOp(BaseOp):
    """Read CSV bytes into DataFrame."""

    class Inputs(BaseInputs):
        src_csv_bytes: bytes
        encoding: str = "utf-8"
        header: int = 0

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        df = pd.read_csv(
            BytesIO(inp.src_csv_bytes),
            encoding=inp.encoding,
            header=inp.header,
        )
        return self.Outputs(df=df).model_dump(mode="python")


register = register_from_steps()
