"""Step: left-join lookup table to add columns to main DataFrame."""

from __future__ import annotations

from typing import Any

import pandas as pd

from flowbook.core.configs.spec_types import LookupTable
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("lookup_table")
class LookupTableOp(BaseOp):
    class Inputs(InputsBase):
        DF = "df"
        LOOKUP_DF = "lookup_df"
        LOOKUP_SPEC_NAME = "lookup_spec_name"
        ON = "on"
        LOOKUP_ON = "lookup_on"
        COLUMNS = "columns"
        REQUIRED = (DF,)
        OPTIONAL = (LOOKUP_DF, LOOKUP_SPEC_NAME, ON, LOOKUP_ON, COLUMNS)

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        df = inputs[self.Inputs.DF]
        if not isinstance(df, pd.DataFrame):
            raise TypeError("lookup_table df must be a DataFrame")
        lookup_df = inputs.get(self.Inputs.LOOKUP_DF)
        lookup_spec_name = inputs.get(self.Inputs.LOOKUP_SPEC_NAME)
        if lookup_df is not None and lookup_spec_name is not None:
            raise ValueError("lookup_table: provide either lookup_df or lookup_spec_name, not both")
        if lookup_df is None and lookup_spec_name is None:
            raise ValueError("lookup_table: provide lookup_df or lookup_spec_name")
        if lookup_df is None:
            if not isinstance(lookup_spec_name, str):
                raise ValueError("lookup_table lookup_spec_name must be a string")
            spec = store.configs.get_spec(LookupTable, lookup_spec_name)
            artifact_key = spec["artifact_key"]
            lookup_df = store.get_df(artifact_key)
        if not isinstance(lookup_df, pd.DataFrame):
            raise TypeError("lookup_table lookup_df must be a DataFrame")
        on = inputs.get(self.Inputs.ON)
        lookup_on = inputs.get(self.Inputs.LOOKUP_ON, on)
        if on is None or lookup_on is None:
            raise ValueError("lookup_table requires on (and optionally lookup_on)")
        key_col = str(lookup_on)
        columns = inputs.get(self.Inputs.COLUMNS)
        if not columns:
            return {self.Outputs.DF: df}
        if isinstance(columns, str):
            columns = [columns]
        lookup_cols = [c for c in columns if c in lookup_df.columns]
        if not lookup_cols:
            return {self.Outputs.DF: df}
        subset_cols: list[str] = [key_col]
        right = lookup_df[[key_col] + lookup_cols].drop_duplicates(subset=subset_cols).copy()  # pyright: ignore[reportCallIssue]
        merged = pd.merge(
            df,
            right,
            left_on=on,
            right_on=key_col,
            how="left",
            suffixes=("", "_lookup"),
        )
        if key_col != on and key_col in merged.columns:
            merged = merged.drop(columns=[key_col])
        return {self.Outputs.DF: merged}


register = register_from_steps()
