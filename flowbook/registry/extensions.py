from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def _iter_submodules(pkg: ModuleType) -> list[str]:
    names: list[str] = []
    for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        names.append(m.name)
    return names


def register_steps(registry, package: str = "extensions.steps") -> None:
    """
    Load modules under `extensions.steps.*` and call `register(registry)` if present.
    Repo root must be on sys.path (true when running from repo root).
    """
    pkg = importlib.import_module(package)

    for mod_name in _iter_submodules(pkg):
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, "register", None)
        if callable(fn):
            fn(registry)
