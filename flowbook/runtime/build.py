"""
build:
- Construct a pipeline from profile and config
- Pipeline is an executable sequence of steps (serial by default)
Not included:
- Execution
- DAG, branching, or optimization
"""

from __future__ import annotations

from flowbook.runtime.types import Pipeline, Profile, Step


"""
build:
- Construct a pipeline from profile and config
- Pipeline is an executable sequence of steps (serial by default)
Not included:
- Execution
- DAG, branching, or optimization
"""


def build(profile: Profile, config: dict) -> Pipeline:
    # profile currently opaque; config drives pipeline
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
