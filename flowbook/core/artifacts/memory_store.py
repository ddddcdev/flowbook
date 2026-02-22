from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from flowbook.core.artifacts.store import ArtifactNotFound, ArtifactsStore, JsonValue


def _pd() -> Any:
    """Lazy import to keep core import-safe (no pandas at import time)."""
    import pandas as pd

    return pd


@dataclass
class InMemoryArtifactsStore(ArtifactsStore):
    """In-memory artifact store for single-run execution only.

    Does not support runs, entity_runs, or persistence across sessions.
    Use for development and smoke tests only. For multi-run and history,
    use PostgresArtifactsStore with FLOWBOOK_DATABASE_URL.
    """

    _data: dict[str, object] = field(default_factory=dict)

    # ---- JSON only ----
    def put(self, key: str, value: JsonValue, **kwargs: object) -> str:
        # JSON限定を"仕様"として固定
        try:
            json.dumps(value)
        except TypeError as e:
            raise TypeError(f"put expects JSON-serializable value: key={key}") from e

        self._data[key] = value
        return key

    def get(self, key: str) -> JsonValue:
        if key not in self._data:
            raise ArtifactNotFound(key)
        v = self._data[key]
        return v  # type: ignore[return-value]

    def get_dict(self, key: str) -> dict[str, Any]:
        v = self.get(key)
        if not isinstance(v, dict):
            raise TypeError(f"artifact is not a dict: {key}")
        return v

    def list(self, prefix: str | None = None) -> list[str]:
        keys = sorted(self._data.keys())
        if prefix is None:
            return keys
        return [k for k in keys if k.startswith(prefix)]

    # ---- bytes ----
    def put_bytes(self, key: str, data: bytes, **kwargs: object) -> str:
        self._data[key] = bytes(data)
        return key

    def get_bytes(self, key: str) -> bytes:
        b = self.get_any(key)
        if not isinstance(b, (bytes, bytearray)):
            raise TypeError(f"artifact is not bytes: {key}")
        return bytes(b)

    # ---- df (lazy pandas) ----
    def put_df(self, key: str, df: Any, **kwargs: object) -> str:
        pd = _pd()
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"put_df expects pandas.DataFrame; got {type(df).__name__}")
        self._data[key] = df
        return key

    def get_df(self, key: str) -> Any:
        v = self.get_any(key)
        pd = _pd()
        if not isinstance(v, pd.DataFrame):
            raise TypeError(f"artifact is not DataFrame: {key}")
        return v

    # ---- internal helpers ----
    def get_any(self, key: str) -> Any:
        if key not in self._data:
            raise ArtifactNotFound(key)
        v = self._data[key]
        return v  # type: ignore[return-value]
