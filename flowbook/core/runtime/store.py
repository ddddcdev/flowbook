from __future__ import annotations

from typing import Protocol

from flowbook.core.artifacts.store import ArtifactsStore
from flowbook.core.configs.store import ConfigStore


class RunStore(ArtifactsStore, Protocol):
    configs: ConfigStore
