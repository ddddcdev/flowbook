"""Step: conditionally update target columns from source (DataFrame by key or constant)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("conditional_update")
class ConditionalUpdateOp(BaseOp):
    class Inputs(InputsBase):
        DF = "df"
        CONDITION = "condition"
        SOURCE = "source"
        COLUMNS = "columns"
        KEY = "key"
        SOURCE_COLUMNS = "source_columns"
        REQUIRED = (DF, CONDITION, SOURCE, COLUMNS)
        OPTIONAL = (KEY, SOURCE_COLUMNS)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        df = inputs[self.Inputs.DF]
        if not isinstance(df, pd.DataFrame):
            raise TypeError("conditional_update df must be a DataFrame")
        condition = inputs[self.Inputs.CONDITION]
        if not isinstance(condition, str):
            raise TypeError("conditional_update condition must be a string expr")
        source = inputs[self.Inputs.SOURCE]
        columns = inputs[self.Inputs.COLUMNS]
        if isinstance(columns, str):
            columns = [columns]
        key = inputs.get(self.Inputs.KEY)
        source_columns = inputs.get(self.Inputs.SOURCE_COLUMNS)
        if isinstance(source_columns, str):
            source_columns = [source_columns]
        out = df.copy()
        try:
            mask = out.eval(condition, engine="python")
        except Exception as e:
            raise ValueError(f"conditional_update condition failed: {condition!r}") from e
        if not mask.any():
            return {self.Outputs.DF: out}
        if isinstance(source, pd.DataFrame):
            if key is None:
                raise ValueError("conditional_update: key required when source is DataFrame")
            if source_columns is None:
                source_columns = columns
            if len(source_columns) != len(columns):
                raise ValueError("conditional_update: source_columns and columns length must match")
            src = source.set_index(key)
            for tcol, scol in zip(columns, source_columns, strict=True):
                if tcol not in out.columns:
                    out[tcol] = None
                out.loc[mask, tcol] = out.loc[mask, key].map(src[scol].to_dict()).values
        else:
            for col in columns:
                if col not in out.columns:
                    out[col] = None
                out.loc[mask, col] = source
        return {self.Outputs.DF: out}


register = register_from_steps()
