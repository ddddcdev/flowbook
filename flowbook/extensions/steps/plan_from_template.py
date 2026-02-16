from __future__ import annotations

from typing import Any

from flowbook.core.configs.spec_types import PlanTemplate
from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("plan_from_template")
class PlanFromTemplateOp(BaseOp):
    class Inputs(InputsBase):
        TEMPLATE_NAME = "template_name"
        REQUIRED = (TEMPLATE_NAME,)
        OPTIONAL = ()

    class Outputs(OutputsBase):
        PLAN = "plan"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        template_name = inputs[self.Inputs.TEMPLATE_NAME]

        try:
            tmpl = store.configs.get_spec(PlanTemplate, template_name)
        except KeyError as e:
            raise KeyError(f"plan_template '{template_name}' not found") from e

        if "plan" not in tmpl:
            raise KeyError(
                f"plan_template '{template_name}' missing 'plan' key. "
                f"Available keys: {list(tmpl.keys())}"
            )

        plan = tmpl["plan"]
        if not isinstance(plan, dict):
            raise TypeError(
                f"plan_template '{template_name}' has 'plan' key, but it is not a dict. "
                f"Got {type(plan).__name__}: {plan}"
            )

        return {self.Outputs.PLAN: plan}


register = register_from_steps()
