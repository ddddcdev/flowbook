"""
build:
- Construct a pipeline from and config
- Pipeline is an executable sequence of steps (serial by default)
Not included:
- Execution
- DAG, branching, or optimization
"""

from __future__ import annotations

from flowbook.runtime.types import Pipeline, Step


def build(config: dict) -> Pipeline:
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
                outputs=list(s.get("outputs", [])),
            )
        )
    return Pipeline(steps=steps)
