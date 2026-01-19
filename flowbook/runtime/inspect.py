"""
inspect:
- Lightly observe the input and return a profile
- No execution, no side effects
- Only cheap signals (type, size, basic hints)
Not included:
- IO access
- Heavy schema inference
"""

from __future__ import annotations

from typing import Any

from flowbook.runtime.types import Profile


"""
inspect:
- Lightly observe the input and return a profile
- No execution, no side effects
- Only cheap signals (type, size, basic hints)
Not included:
- IO access
- Heavy schema inference
"""


def inspect(input: Any) -> Profile:
    # Opaque profile (cheap, JSON-friendly)
    return {"raw": input}
