from __future__ import annotations

import importlib
import importlib.metadata
import pkgutil
from types import ModuleType

from flowbook.core.registry.registry import Registry

ENTRY_POINT_GROUP_STEPS = "flowbook.steps"


def _iter_submodules(pkg: ModuleType) -> list[str]:
    names: list[str] = []
    for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        names.append(m.name)
    return names


def register_steps(registry: Registry, package: str = "flowbook.extensions.steps") -> None:
    """
    Load modules under `package.*` and call `register(registry)` if present.
    Used by flowbook's built-in steps plugin (registered via entry point).
    """
    pkg = importlib.import_module(package)

    for mod_name in _iter_submodules(pkg):
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, "register", None)
        if callable(fn):
            fn(registry)


def discover_steps(registry: Registry) -> None:
    """
    Discover and register all steps from the ``flowbook.steps`` entry point group.
    Built-in steps and third-party plugins use the same mechanism; each entry point
    must be a callable(registry) -> None (e.g. register_steps or a project's register).
    """
    eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP_STEPS)
    for ep in eps:
        fn = ep.load()
        if callable(fn):
            fn(registry)
