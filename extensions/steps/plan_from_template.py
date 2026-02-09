from __future__ import annotations


def plan_from_template_op(inputs: dict, store_):
    """
    Load a plan template from ConfigStore and return its plan.

    Policy:
    - Reads template spec from store_.configs.get_spec("plan_template", template_name)
    - Template spec must contain a "plan" key with a dict value
    - Returns {"plan": template_spec["plan"]}
    - Errors if template not found or "plan" key is missing/malformed
    """

    if "template_name" not in inputs:
        raise KeyError("template_name required in inputs")

    template_name = inputs["template_name"]

    # Fetch template from ConfigStore
    try:
        tmpl = store_.configs.get_spec("plan_template", template_name)
    except KeyError as e:
        raise KeyError(f"plan_template '{template_name}' not found") from e

    # Validate template has "plan" key
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


def register(registry) -> None:
    registry.register("plan_from_template", plan_from_template_op)
