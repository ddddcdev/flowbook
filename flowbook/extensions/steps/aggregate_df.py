"""Step: aggregate DataFrame with optional group_by."""

from __future__ import annotations

from typing import Any

import pandas as pd

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("aggregate_df")
class AggregateDfOp(BaseOp):
    class Inputs(InputsBase):
        DF = "df"
        GROUP_BY = "group_by"
        AGG = "agg"
        REQUIRED = (DF, AGG)
        OPTIONAL = (GROUP_BY,)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        df = inputs[self.Inputs.DF]
        if not isinstance(df, pd.DataFrame):
            raise TypeError("aggregate_df df must be a DataFrame")
        agg_spec = inputs[self.Inputs.AGG]
        if not isinstance(agg_spec, dict):
            raise TypeError("aggregate_df agg must be a dict")
        group_by = inputs.get(self.Inputs.GROUP_BY)
        if group_by is not None:
            if isinstance(group_by, str):
                group_by = [group_by]
            out = df.groupby(group_by).agg(agg_spec).reset_index()
        else:
            out = df.agg(agg_spec)
            if isinstance(out, pd.Series):
                out = out.to_frame().T
        return {self.Outputs.DF: out}


register = register_from_steps()
