"""CLI extension discovery via flowbook.cli entry point group."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typer import Typer

ENTRY_POINT_GROUP_CLI = "flowbook.cli"


def discover_cli_extensions(app: Typer) -> None:
    """
    Discover and register all CLI extensions from the ``flowbook.cli`` entry point group.
    Each entry point must be a callable(app: Typer) -> None that adds subcommands or typers.
    flowbook's built-in CLI and third-party packages use the same mechanism.
    """
    eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP_CLI)
    for ep in eps:
        fn = ep.load()
        if callable(fn):
            fn(app)
