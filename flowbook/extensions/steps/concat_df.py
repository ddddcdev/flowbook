"""Step: concatenate DataFrames (vertical or horizontal)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("concat_df")
class ConcatDfOp(BaseOp):
    class Inputs(BaseInputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        dfs: list[DataFrame]
        axis: int = 0
        ignore_index: bool = False
        join: str = "outer"

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        out = pd.concat(
            inp.dfs,
            axis=inp.axis,
            ignore_index=inp.ignore_index,
            join=inp.join,
        )
        assert isinstance(out, pd.DataFrame), "concat of DataFrames yields DataFrame"
        return self.Outputs(df=out).model_dump(mode="python")


register = register_from_steps()
