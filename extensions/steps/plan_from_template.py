from __future__ import annotations

from typing import Any

from flowbook.registry.base_op import BaseOp
from flowbook.registry.registry import Registry
from flowbook.registry.spec import InputsBase
from flowbook.runtime.store import RunStore


class PlanFromTemplateOp(BaseOp):
    class Inputs(InputsBase):
        TEMPLATE_NAME = "template_name"
        REQUIRED = (TEMPLATE_NAME,)
        OPTIONAL = ()

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        template_name = inputs[self.Inputs.TEMPLATE_NAME]

        try:
            tmpl = store.configs.get_spec("plan_template", template_name)
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

        return {"plan": plan}


def register(registry: Registry) -> None:
    registry.register("plan_from_template", PlanFromTemplateOp())
