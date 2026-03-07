"""Step: conditionally update target columns from source (DataFrame by key or constant)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("conditional_update")
class ConditionalUpdateOp(BaseOp):
    class Inputs(BaseInputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame
        condition: str
        source: DataFrame | int | float | str
        columns: list[str] | str
        key: str | None = None
        source_columns: list[str] | str | None = None

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        columns = [inp.columns] if isinstance(inp.columns, str) else list(inp.columns)
        source_columns = (
            [inp.source_columns] if isinstance(inp.source_columns, str) else inp.source_columns
        )
        out = inp.df.copy()
        try:
            mask = out.eval(inp.condition, engine="python")
        except Exception as e:
            raise ValueError(f"conditional_update condition failed: {inp.condition!r}") from e
        if not mask.any():
            return self.Outputs(df=out).model_dump(mode="python")
        if isinstance(inp.source, pd.DataFrame):
            if inp.key is None:
                raise ValueError("conditional_update: key required when source is DataFrame")
            scols = source_columns or columns
            if len(scols) != len(columns):
                raise ValueError("conditional_update: source_columns and columns length must match")
            src = inp.source.set_index(inp.key)
            for tcol, scol in zip(columns, scols, strict=True):
                if tcol not in out.columns:
                    out[tcol] = None
                out.loc[mask, tcol] = out.loc[mask, inp.key].map(src[scol].to_dict()).values
        else:
            for col in columns:
                if col not in out.columns:
                    out[col] = None
                out.loc[mask, col] = inp.source
        return self.Outputs(df=out).model_dump(mode="python")


register = register_from_steps()
