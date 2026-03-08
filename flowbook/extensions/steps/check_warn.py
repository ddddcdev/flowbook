"""Step: evaluate checks on DataFrame; on violation append message to run _warnings."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore
from flowbook.extensions.steps._types import DataFrame


@step("check_warn")
class CheckWarnOp(BaseOp):
    """Run checks on DataFrame. Emits warnings for failures; passes df through."""

    class Inputs(BaseInputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame
        checks: list[dict[str, Any]]

    class Outputs(BaseOutputs):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        df: DataFrame

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)
        warnings: list[str] = []
        for item in inp.checks:
            if not isinstance(item, dict):
                continue
            expr = item.get("expr")
            message = item.get("message", "check failed")
            if not isinstance(expr, str) or not expr.strip():
                continue
            try:
                mask = inp.df.eval(expr, engine="python")
                if getattr(mask, "any", None) and mask.any():
                    warnings.append(str(message))
                elif isinstance(mask, bool) and mask:
                    warnings.append(str(message))
            except Exception:
                warnings.append(str(message))
        result = self.Outputs(df=inp.df).model_dump(mode="python")
        if warnings:
            result["_warnings"] = warnings
        return result


register = register_from_steps()
