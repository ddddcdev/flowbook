from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from flowbook.artifacts.store import ArtifactsStore, JsonValue
from flowbook.configs.store import ConfigStore
from flowbook.runtime.store import RunStore


@dataclass
class DefaultRunStore(RunStore):
    artifacts: ArtifactsStore
    configs: ConfigStore

    def put(self, key: str, value: JsonValue) -> str:
        return self.artifacts.put(key, value)

    def get(self, key: str) -> JsonValue:
        return self.artifacts.get(key)

    def get_dict(self, key: str) -> dict[str, Any]:
        return self.artifacts.get_dict(key)

    def list(self, prefix: str | None = None) -> list[str]:
        return self.artifacts.list(prefix=prefix)

    def put_bytes(self, key: str, data: bytes) -> str:
        return self.artifacts.put_bytes(key, data)

    def get_bytes(self, key: str) -> bytes:
        return self.artifacts.get_bytes(key)

    def put_df(self, key: str, df: pd.DataFrame) -> str:
        return self.artifacts.put_df(key, df)

    def get_df(self, key: str) -> pd.DataFrame:
        return self.artifacts.get_df(key)
