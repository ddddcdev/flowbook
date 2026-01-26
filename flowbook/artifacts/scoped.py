from dataclasses import dataclass
from typing import Any, Mapping, Optional

import pandas as pd


def scope_key(run_id: str, key: str) -> str:
    if not run_id:
        raise ValueError("run_id must be a non-empty string")
    return key if key.startswith(f"{run_id}/") else f"{run_id}/{key}"


@dataclass
class RunScopedStore:
    base: Any
    run_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ValueError("run_id must be a non-empty string")

    # --- InMemory互換（必須） ---
    def put(self, key: str, value: Any) -> str:
        return self.base.put(scope_key(self.run_id, key), value)

    def get(self, key: str) -> Any:
        return self.base.get(scope_key(self.run_id, key))

    def list(self, prefix: str | None = None) -> list[str]:
        if prefix is None:
            return self.base.list(prefix=f"{self.run_id}/")
        return self.base.list(prefix=scope_key(self.run_id, prefix))

    # --- typed helpers（Postgres向け） ---
    def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        meta: Optional[Mapping[str, Any]] = None,
    ) -> None:
        return self.base.put_bytes(
            scope_key(self.run_id, key), data, content_type=content_type, meta=meta
        )

    def get_bytes(self, key: str) -> bytes:
        return self.base.get_bytes(scope_key(self.run_id, key))

    def put_json(
        self, key: str, obj: Any, *, meta: Optional[Mapping[str, Any]] = None
    ) -> None:
        return self.base.put_json(scope_key(self.run_id, key), obj, meta=meta)

    def get_json(self, key: str) -> Any:
        return self.base.get_json(scope_key(self.run_id, key))

    def put_df(
        self, key: str, df: pd.DataFrame, *, meta: Optional[Mapping[str, Any]] = None
    ) -> None:
        return self.base.put_df(scope_key(self.run_id, key), df, meta=meta)

    def get_df(self, key: str) -> pd.DataFrame:
        return self.base.get_df(scope_key(self.run_id, key))
