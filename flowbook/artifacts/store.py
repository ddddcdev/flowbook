from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

import pandas as pd


class ArtifactNotFound(KeyError):
    """Raised when an artifact key does not exist in store."""


@dataclass
class InMemoryArtifactsStore:
    _data: dict[str, Any] = field(default_factory=dict)

    def put(self, key: str, value: Any) -> str:
        self._data[key] = value
        return key

    def get(self, key: str) -> Any:
        if key not in self._data:
            raise ArtifactNotFound(key)
        return self._data[key]

    def list(self, prefix: str | None = None) -> list[str]:
        keys = sorted(self._data.keys())
        if prefix is None:
            return keys
        return [k for k in keys if k.startswith(prefix)]

    # --- typed helpers (Postgres互換のために追加) ---
    def put_json(
        self, key: str, obj: Any, *, meta: Optional[Mapping[str, Any]] = None
    ) -> None:
        _ = meta
        self.put(key, obj)

    def get_json(self, key: str) -> Any:
        return self.get(key)

    def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        meta: Optional[Mapping[str, Any]] = None,
    ) -> None:
        _ = (content_type, meta)
        self.put(key, data)

    def get_bytes(self, key: str) -> bytes:
        b = self.get(key)
        if not isinstance(b, (bytes, bytearray)):
            raise TypeError(f"artifact is not bytes: {key}")
        return bytes(b)

    def put_df(
        self, key: str, df: pd.DataFrame, *, meta: Optional[Mapping[str, Any]] = None
    ) -> None:
        _ = meta
        self.put(key, df)

    def get_df(self, key: str) -> pd.DataFrame:
        df = self.get(key)
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"artifact is not DataFrame: {key}")
        return df
