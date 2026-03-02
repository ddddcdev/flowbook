from __future__ import annotations

from typing import Any

from flowbook.core.configs.spec_types import Plan
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("load_plan")
class LoadPlanOp(BaseOp):
    class Inputs(InputsBase):
        PLAN_NAME = "plan_name"
        REQUIRED = (PLAN_NAME,)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        PLAN = "plan"
        RESULT_ARTIFACTS = "result_artifacts"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        plan_name = inputs[self.Inputs.PLAN_NAME]

        try:
            spec = store.configs.get_spec(Plan, plan_name)
        except KeyError as e:
            raise KeyError(f"plan '{plan_name}' not found") from e

        if "plan" not in spec:
            raise KeyError(
                f"plan '{plan_name}' missing 'plan' key. "
                f"Available keys: {list(spec.keys())}"
            )

        plan = spec["plan"]
        if not isinstance(plan, dict):
            raise TypeError(
                f"plan '{plan_name}' has 'plan' key, but it is not a dict. "
                f"Got {type(plan).__name__}: {plan}"
            )

        out: dict[str, Any] = {self.Outputs.PLAN: plan}
        if "result_artifacts" in spec and spec["result_artifacts"]:
            out["result_artifacts"] = spec["result_artifacts"]
        return out


register = register_from_steps()
