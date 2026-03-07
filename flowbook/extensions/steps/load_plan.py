from __future__ import annotations

from typing import Any

from pydantic import Field

from flowbook.core.configs.spec_types import Plan
from flowbook.core.registry.base_op import BaseInputs, BaseOp, BaseOutputs
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("load_plan")
class LoadPlanOp(BaseOp):
    """Load plan config by name from ConfigStore. Used by Import/Export planner."""
    class Inputs(BaseInputs):
        plan_name: str = Field(json_schema_extra={"x-config-kind": Plan.KIND})

    class Outputs(BaseOutputs):
        plan: dict[str, Any]
        result_artifacts: list[dict[str, Any]] | None = None

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        inp = self.Inputs.model_validate(inputs)

        try:
            spec = store.configs.get_spec(Plan, inp.plan_name)
        except KeyError as e:
            raise KeyError(f"plan '{inp.plan_name}' not found") from e

        if "plan" not in spec:
            raise KeyError(
                f"plan '{inp.plan_name}' missing 'plan' key. Available keys: {list(spec.keys())}"
            )

        plan = spec["plan"]
        if not isinstance(plan, dict):
            raise TypeError(
                f"plan '{inp.plan_name}' has 'plan' key, but it is not a dict. "
                f"Got {type(plan).__name__}: {plan}"
            )

        kwargs: dict[str, Any] = {"plan": plan}
        if "result_artifacts" in spec and spec["result_artifacts"]:
            kwargs["result_artifacts"] = spec["result_artifacts"]
        return self.Outputs(**kwargs).model_dump(mode="python")


register = register_from_steps()
