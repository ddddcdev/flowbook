from __future__ import annotations

from typing import Protocol

from flowbook.artifacts.store import ArtifactsStore
from flowbook.configs.store import ConfigStore


class RunStore(ArtifactsStore, Protocol):
    configs: ConfigStore
