from __future__ import annotations

from typing import Any, Protocol


class ConfigStore(Protocol):
    def get_spec(self, kind: str, name: str) -> dict[str, Any]: ...

    def put_spec(self, kind: str, name: str, spec: dict[str, Any], *, config_id: str) -> None: ...
