from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from flowbook.artifacts.store import ArtifactsStore, JsonValue


def scope_key(run_id: str, key: str) -> str:
    return f"{run_id}/{key}"


@dataclass(frozen=True)
class RunScopedStore:
    base: ArtifactsStore
    run_id: str

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must be non-empty")

    def put(self, key: str, value: JsonValue) -> str:
        return self.base.put(scope_key(self.run_id, key), value)

    def get(self, key: str) -> JsonValue:
        return self.base.get(scope_key(self.run_id, key))

    def list(self, prefix: str | None = None) -> list[str]:
        scoped_prefix = None if prefix is None else scope_key(self.run_id, prefix)
        return self.base.list(scoped_prefix)

    def put_bytes(self, key: str, data: bytes) -> str:
        return self.base.put_bytes(scope_key(self.run_id, key), data)

    def get_bytes(self, key: str) -> bytes:
        return self.base.get_bytes(scope_key(self.run_id, key))

    def put_df(self, key: str, df: "pd.DataFrame") -> str:
        return self.base.put_df(scope_key(self.run_id, key), df)

    def get_df(self, key: str) -> "pd.DataFrame":
        return self.base.get_df(scope_key(self.run_id, key))
