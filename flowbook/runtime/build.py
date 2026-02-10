"""
build:
- Construct a pipeline from and config
- Pipeline is an executable sequence of steps (serial by default)
Not included:
- Execution
- DAG, branching, or optimization
"""

from __future__ import annotations

from typing import Any

from flowbook.runtime.types import Pipeline, Step


def build(config: dict[str, Any]) -> Pipeline:
    steps_cfg = config.get("steps", [])
    if not isinstance(steps_cfg, list):
        raise ValueError("config.steps must be a list")

    steps: list[Step] = []
    for s in steps_cfg:
        steps.append(
            Step(
                name=s["name"],
                op=s["op"],
                inputs=dict(s.get("inputs", {})),
            )
        )
    return Pipeline(steps=steps)
