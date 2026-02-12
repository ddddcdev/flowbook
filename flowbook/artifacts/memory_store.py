from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from flowbook.artifacts.store import ArtifactNotFound, ArtifactsStore, JsonValue


@dataclass
class InMemoryArtifactsStore(ArtifactsStore):
    _data: dict[str, object] = field(default_factory=dict)

    # ---- JSON only ----
    def put(self, key: str, value: JsonValue) -> str:
        # JSON限定を“仕様”として固定
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
        # ランタイム安全柵（壊れてたら即発見）
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
    def put_bytes(self, key: str, data: bytes) -> str:
        self._data[key] = bytes(data)
        return key

    def get_bytes(self, key: str) -> bytes:
        b = self.get_any(key)
        if not isinstance(b, (bytes, bytearray)):
            raise TypeError(f"artifact is not bytes: {key}")
        return bytes(b)

    # ---- df ----
    def put_df(self, key: str, df: pd.DataFrame) -> str:
        self._data[key] = df
        return key

    def get_df(self, key: str) -> pd.DataFrame:
        v = self.get_any(key)
        if not isinstance(v, pd.DataFrame):
            raise TypeError(f"artifact is not DataFrame: {key}")
        return v

    # ---- internal helpers ----
    def get_any(self, key: str) -> JsonValue | bytes | pd.DataFrame:
        if key not in self._data:
            raise ArtifactNotFound(key)
        v = self._data[key]
        return v  # type: ignore[return-value]
