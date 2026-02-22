"""
Runtime types:
- Thin definitions for plan, step_spec, run_info
Rule:
- No semantics
- No implementation details
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Step:
    name: str
    op: str
    inputs: dict[str, Any]  # param -> value (ref string @..., literal, or nested dict/list)


@dataclass(frozen=True)
class Plan:
    steps: list[Step]


@dataclass
class StepRunInfo:
    name: str
    status: str
    inputs: dict[str, Any]
    outputs: dict[str, str] = field(default_factory=dict)
    error: str | None = None


@dataclass
class RunInfo:
    run_id: str
    status: str
    steps: list[StepRunInfo] = field(default_factory=list)
    artifacts_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
