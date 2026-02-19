"""Step: merge two DataFrames (join) on key column(s)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("merge_df")
class MergeDfOp(BaseOp):
    class Inputs(InputsBase):
        LEFT = "left"
        RIGHT = "right"
        ON = "on"
        LEFT_ON = "left_on"
        RIGHT_ON = "right_on"
        HOW = "how"
        REQUIRED = (LEFT, RIGHT)
        OPTIONAL = (ON, LEFT_ON, RIGHT_ON, HOW)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        left = inputs[self.Inputs.LEFT]
        right = inputs[self.Inputs.RIGHT]
        if not isinstance(left, pd.DataFrame) or not isinstance(right, pd.DataFrame):
            raise TypeError("merge_df left and right must be DataFrames")
        how = inputs.get(self.Inputs.HOW, "inner")
        kwargs: dict[str, Any] = {"how": how}
        if self.Inputs.ON in inputs:
            kwargs["on"] = inputs[self.Inputs.ON]
        if self.Inputs.LEFT_ON in inputs:
            kwargs["left_on"] = inputs[self.Inputs.LEFT_ON]
        if self.Inputs.RIGHT_ON in inputs:
            kwargs["right_on"] = inputs[self.Inputs.RIGHT_ON]
        out = pd.merge(left, right, **kwargs)
        return {self.Outputs.DF: out}


register = register_from_steps()
