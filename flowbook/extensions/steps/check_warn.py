"""Step: evaluate checks on DataFrame; on violation append message to run _warnings."""

from __future__ import annotations

from typing import Any

import pandas as pd

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("check_warn")
class CheckWarnOp(BaseOp):
    class Inputs(InputsBase):
        DF = "df"
        CHECKS = "checks"
        REQUIRED = (DF, CHECKS)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        DF = "df"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        df = inputs[self.Inputs.DF]
        if not isinstance(df, pd.DataFrame):
            raise TypeError("check_warn df must be a DataFrame")
        checks = inputs[self.Inputs.CHECKS]
        if not isinstance(checks, list):
            raise TypeError("check_warn checks must be a list")
        warnings: list[str] = []
        for item in checks:
            if not isinstance(item, dict):
                continue
            expr = item.get("expr")
            message = item.get("message", "check failed")
            if not isinstance(expr, str) or not expr.strip():
                continue
            try:
                mask = df.eval(expr, engine="python")
                if getattr(mask, "any", None) and mask.any():
                    warnings.append(str(message))
                elif isinstance(mask, bool) and mask:
                    warnings.append(str(message))
            except Exception:
                warnings.append(str(message))
        result: dict[str, Any] = {self.Outputs.DF: df}
        if warnings:
            result["_warnings"] = warnings
        return result


register = register_from_steps()
