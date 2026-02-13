"""
Flowbook: pipeline runner and artifact store.

Public API (a1 minimum): Engine, Registry, RunSession, register_steps, and stores.
Use ``from flowbook import Engine, Registry, register_steps, ...`` for short imports.
Everything else: ``flowbook.core.*``.
"""

from __future__ import annotations

from flowbook.core.artifacts.memory_store import InMemoryArtifactsStore
from flowbook.core.artifacts.store import ArtifactsStore
from flowbook.core.configs.memory_store import InMemoryConfigStore
from flowbook.core.configs.null_store import NullConfigStore
from flowbook.core.engine.engine import Engine
from flowbook.core.engine.session import RunSession
from flowbook.core.registry.extensions import register_steps
from flowbook.core.registry.registry import Registry, UnknownOp
from flowbook.core.runtime.default_store import DefaultRunStore


def _version() -> str:
    try:
        import importlib.metadata as _metadata
    except ImportError:
        return "0.0.0"
    try:
        return _metadata.version("flowbook")
    except _metadata.PackageNotFoundError:
        return "0.0.0"


__version__ = _version()

__all__ = [
    "ArtifactsStore",
    "DefaultRunStore",
    "Engine",
    "InMemoryArtifactsStore",
    "InMemoryConfigStore",
    "NullConfigStore",
    "Registry",
    "RunSession",
    "UnknownOp",
    "register_steps",
    "__version__",
]
