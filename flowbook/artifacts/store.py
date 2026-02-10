from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd

# ---- JSON typing ----
JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


class ArtifactNotFound(KeyError):
    """Raised when an artifact key does not exist in store."""


@runtime_checkable
class ArtifactsStore(Protocol):
    """Use get_dict(key) when the artifact is a dict (e.g. inspect result, plan).
    Use get(key) for other JsonValue (primitives, lists)."""

    def put(self, key: str, value: JsonValue) -> str: ...
    def get(self, key: str) -> JsonValue: ...
    def list(self, prefix: str | None = None) -> list[str]: ...

    def get_dict(self, key: str) -> dict[str, Any]: ...

    def put_bytes(self, key: str, data: bytes) -> str: ...
    def get_bytes(self, key: str) -> bytes: ...

    def put_df(self, key: str, df: pd.DataFrame) -> str: ...
    def get_df(self, key: str) -> pd.DataFrame: ...
