"""
build:
- Construct a pipeline from a pipeline config (steps list).
- Pipeline is an executable sequence of steps (serial by default)
Not included:
- Execution
- DAG, branching, or optimization
"""

from __future__ import annotations

from typing import Any

from flowbook.core.runtime.types import Pipeline, Step


def build(pipeline_config: dict[str, Any]) -> Pipeline:
    step_configs = pipeline_config.get("steps", [])
    if not isinstance(step_configs, list):
        raise ValueError("pipeline_config.steps must be a list")

    steps: list[Step] = []
    for step_cfg in step_configs:
        steps.append(
            Step(
                name=step_cfg["name"],
                op=step_cfg["op"],
                inputs=dict(step_cfg.get("inputs", {})),
            )
        )
    return Pipeline(steps=steps)
