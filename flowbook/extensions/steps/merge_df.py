"""Step: merge two DataFrames (join) on key column(s)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("merge_df")
class MergeDfOp(BaseOp):
    class Inputs(BaseInputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        left: DataFrame
        right: DataFrame
        on: str | list[str] | None = None
        left_on: str | list[str] | None = None
        right_on: str | list[str] | None = None
        how: str = "inner"

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        kwargs: dict[str, Any] = {"how": inp.how}
        if inp.on is not None:
            kwargs["on"] = inp.on
        if inp.left_on is not None:
            kwargs["left_on"] = inp.left_on
        if inp.right_on is not None:
            kwargs["right_on"] = inp.right_on
        out = pd.merge(inp.left, inp.right, **kwargs)
        return self.Outputs(df=out).model_dump(mode="python")


register = register_from_steps()
