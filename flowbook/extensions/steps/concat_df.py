"""Step: concatenate DataFrames (vertical or horizontal)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("concat_df")
class ConcatDfOp(BaseOp):
    class Inputs(InputsBase):
        DFS = "dfs"
        AXIS = "axis"
        IGNORE_INDEX = "ignore_index"
        JOIN = "join"
        REQUIRED = (DFS,)
        OPTIONAL = (AXIS, IGNORE_INDEX, JOIN)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        dfs = inputs[self.Inputs.DFS]
        if not isinstance(dfs, list):
            raise TypeError("concat_df dfs must be a list")
        for i, d in enumerate(dfs):
            if not isinstance(d, pd.DataFrame):
                raise TypeError(f"concat_df dfs[{i}] must be a DataFrame")
        axis = inputs.get(self.Inputs.AXIS, 0)
        ignore_index = inputs.get(self.Inputs.IGNORE_INDEX, False)
        join = inputs.get(self.Inputs.JOIN, "outer")
        out = pd.concat(dfs, axis=axis, ignore_index=ignore_index, join=join)
        return {self.Outputs.DF: out}


register = register_from_steps()
