"""Step: left-join lookup table to add columns to main DataFrame."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import ConfigDict, Field

from flowbook.core.configs.spec_types import LookupTable
from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("lookup_table")
class LookupTableOp(BaseOp):
    """Left-join DataFrame with lookup table (from config or inline df)."""

    class Inputs(BaseInputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame = Field(description="DataFrame")
        lookup_df: DataFrame | None = Field(None, description="DataFrame or from lookup_spec_name")
        lookup_spec_name: str | None = Field(
            None, json_schema_extra={"x-config-kind": LookupTable.KIND}
        )
        on: str | None = None
        lookup_on: str | None = None
        columns: list[str] | str | None = None

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        lookup_df: pd.DataFrame | None = inp.lookup_df
        if lookup_df is not None and inp.lookup_spec_name is not None:
            raise ValueError("lookup_table: provide either lookup_df or lookup_spec_name, not both")
        if lookup_df is None and inp.lookup_spec_name is None:
            raise ValueError("lookup_table: provide lookup_df or lookup_spec_name")
        if lookup_df is None:
            name = inp.lookup_spec_name
            if name is None:
                raise ValueError("lookup_table: provide lookup_df or lookup_spec_name")
            spec = store.configs.get_spec(LookupTable, name)
            lookup_df = store.get_df(spec["artifact_key"])
        assert lookup_df is not None
        on = inp.on
        lookup_on = inp.lookup_on or on
        if on is None or lookup_on is None:
            raise ValueError("lookup_table requires on (and optionally lookup_on)")
        key_col = str(lookup_on)
        columns = inp.columns
        if not columns:
            return self.Outputs(df=inp.df).model_dump(mode="python")
        cols_list = [columns] if isinstance(columns, str) else list(columns)
        lookup_cols = [c for c in cols_list if c in lookup_df.columns]
        if not lookup_cols:
            return self.Outputs(df=inp.df).model_dump(mode="python")
        subset_cols: list[str] = [key_col]
        right = lookup_df[[key_col] + lookup_cols].drop_duplicates(subset=subset_cols).copy()  # pyright: ignore[reportCallIssue]
        merged = pd.merge(
            inp.df,
            right,
            left_on=on,
            right_on=key_col,
            how="left",
            suffixes=("", "_lookup"),
        )
        if key_col != on and key_col in merged.columns:
            merged = merged.drop(columns=[key_col])
        return self.Outputs(df=merged).model_dump(mode="python")


register = register_from_steps()
