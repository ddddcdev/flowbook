from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowbook.core.artifacts.store import ArtifactsStore, JsonValue
from flowbook.core.configs.store import ConfigStore
from flowbook.core.runtime.store import RunStore


@dataclass
class DefaultRunStore(RunStore):
    artifacts: ArtifactsStore
    configs: ConfigStore

    def put(self, key: str, value: JsonValue, **kwargs: Any) -> str:
        return self.artifacts.put(key, value, **kwargs)

    def get(self, key: str) -> JsonValue:
        return self.artifacts.get(key)

    def get_dict(self, key: str) -> dict[str, Any]:
        return self.artifacts.get_dict(key)

    def list(self, prefix: str | None = None) -> list[str]:
        return self.artifacts.list(prefix=prefix)

    def put_bytes(self, key: str, data: bytes, **kwargs: Any) -> str:
        return self.artifacts.put_bytes(key, data, **kwargs)

    def get_bytes(self, key: str) -> bytes:
        return self.artifacts.get_bytes(key)

    def put_df(self, key: str, df: Any, **kwargs: Any) -> str:
        return self.artifacts.put_df(key, df, **kwargs)

    def get_df(self, key: str) -> Any:
        return self.artifacts.get_df(key)

    def get_any(self, key: str) -> Any:
        return self.artifacts.get_any(key)

    def upsert_entity_run(
        self,
        run_id: str,
        entity_key: str,
        status: str,
        run_config_json: str | None = None,
        entity_config_json: str | None = None,
        result_artifacts: list[dict[str, str | None]] | None = None,
    ) -> None:
        """Upsert entity_runs if underlying artifacts store supports it."""
        upsert = getattr(self.artifacts, "upsert_entity_run", None)
        if callable(upsert):
            upsert(
                run_id,
                entity_key,
                status,
                run_config_json=run_config_json,
                entity_config_json=entity_config_json,
                result_artifacts=result_artifacts,
            )
