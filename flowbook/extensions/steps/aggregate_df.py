"""Step: aggregate DataFrame with optional group_by."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("aggregate_df")
class AggregateDfOp(BaseOp):
    """Aggregate DataFrame by group_by with agg dict (col -> sum, mean, etc.)."""

    class Inputs(BaseInputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame
        agg: dict[str, Any]
        group_by: str | list[str] | None = None

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        group_by = inp.group_by
        if group_by is not None:
            keys = [group_by] if isinstance(group_by, str) else list(group_by)
            out = inp.df.groupby(keys).agg(inp.agg).reset_index()
        else:
            out = inp.df.agg(inp.agg)
            if isinstance(out, pd.Series):
                out = out.to_frame().T
        return self.Outputs(df=out).model_dump(mode="python")


register = register_from_steps()
