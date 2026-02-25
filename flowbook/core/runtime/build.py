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

from flowbook.core.runtime.types import Plan, ResultArtifact, Step


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

    result_artifacts: list[ResultArtifact] | None = None
    raw = plan_config.get("result_artifacts")
    if isinstance(raw, list) and raw:
        result_artifacts = []
        for item in raw:
            if isinstance(item, dict) and "step" in item and "key" in item:
                path = f"{item['step']}/{item['key']}"
                label = item.get("label") if isinstance(item.get("label"), str) else None
                result_artifacts.append(ResultArtifact(path=path, label=label))
            else:
                raise ValueError(
                    f"result_artifacts entry must have step and key: {item!r}"
                )

    return Plan(steps=steps, result_artifacts=result_artifacts)
