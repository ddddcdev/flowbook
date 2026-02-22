"""
build:
- Construct a plan from a plan config (steps list).
- Plan is an executable sequence of steps (serial by default)
Not included:
- Execution
- DAG, branching, or optimization
"""

from __future__ import annotations

from typing import Any

from flowbook.core.runtime.types import Plan, Step


def build(plan_config: dict[str, Any]) -> Plan:
    step_configs = plan_config.get("steps", [])
    if not isinstance(step_configs, list):
        raise ValueError("plan_config.steps must be a list")

    steps: list[Step] = []
    for step_cfg in step_configs:
        steps.append(
            Step(
                name=step_cfg["name"],
                op=step_cfg["op"],
                inputs=dict(step_cfg.get("inputs", {})),
            )
        )
    return Plan(steps=steps)
