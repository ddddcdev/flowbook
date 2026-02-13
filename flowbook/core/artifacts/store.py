from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

# ---- JSON typing ----
JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]

# DataFrame in protocol: use Any to avoid importing pandas at import time (core stays light).
DataFrameAny = Any


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

    def put_df(self, key: str, df: DataFrameAny) -> str: ...
    def get_df(self, key: str) -> DataFrameAny: ...

    def get_any(self, key: str) -> JsonValue | bytes | DataFrameAny: ...
