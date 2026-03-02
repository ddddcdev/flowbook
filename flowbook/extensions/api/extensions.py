"""API extension discovery via flowbook.api entry point group."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

ENTRY_POINT_GROUP_API = "flowbook.api"


def discover_api_extensions(app: FastAPI) -> None:
    """
    Discover and register all API extensions from the ``flowbook.api`` entry point group.
    Each entry point must be a callable(app: FastAPI) -> None that adds routers or routes.
    flowbook's built-in API and third-party packages use the same mechanism.
    """
    eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP_API)
    for ep in eps:
        fn = ep.load()
        if callable(fn):
            fn(app)
