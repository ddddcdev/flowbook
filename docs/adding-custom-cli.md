# Adding custom CLI commands

This guide shows how to add your own subcommands to the `flowbook` CLI so they appear alongside built-in commands like `flowbook db` and `flowbook streamlit`.

## Overview

flowbook discovers CLI extensions from the `flowbook.cli` entry point group. Each entry point is a callable `(app: Typer) -> None` that adds subcommands or Typer sub-apps to the main app.

**Requirements**: `flowbook[dev]` (typer, rich, httpx) must be installed for the extended CLI to load.

## Minimal: register function in your project

You can add CLI commands without packaging by calling `register` yourself before flowbook runs. For the standard flowbook entry point, you need to register via the discovery mechanism. The simplest approach is to use an installable package with an entry point (see below). If your project is a script or application (not a distributable package), you can still extend the CLI by ensuring your register is invoked—see "Direct registration" below.

## Package with entry point (recommended)

1. **Implement a register function** in your package that receives the Typer app and adds subcommands:

```python
# my_project/cli_plugin.py
import typer

def register_cli(app: typer.Typer) -> None:
    """Add my_project commands to flowbook CLI."""
    my_app = typer.Typer(help="My project commands.")

    @my_app.command("hello")
    def hello(name: str = typer.Argument("World", help="Name to greet")) -> None:
        typer.echo(f"Hello, {name}!")

    app.add_typer(my_app, name="myproject")
```

2. **Declare the entry point** in your package's `pyproject.toml`:

```toml
[project.entry-points."flowbook.cli"]
my_project = "my_project.cli_plugin:register_cli"
```

3. **Install** your package in the same environment as flowbook (`pip install -e .` or `poetry install`).

4. **Run** `flowbook myproject hello` — your command is available alongside flowbook's built-in commands.

## Direct registration (without entry point)

If you control the flowbook invocation (e.g. you have a wrapper script or launcher), you can create the Typer app, call your register, and then run it. This avoids entry points but requires you to use flowbook's CLI machinery directly. For most users, the entry point approach is simpler.

## Running a custom Streamlit app

flowbook's built-in `flowbook streamlit` launches a fixed demo UI. To run your own Streamlit app, you have two options:

1. **Add a CLI command** via the entry point that runs your app:

```python
def register_cli(app: typer.Typer) -> None:
    @app.command("my-ui")
    def my_ui() -> None:
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "streamlit", "run", "my_project/dashboard.py"])
```

   Then run `flowbook my-ui`.

2. **Run Streamlit directly** (no flowbook involvement):

```sh
streamlit run my_project/dashboard.py
```

## Summary

| Approach | Use case |
|----------|----------|
| Package + entry point | Add reusable commands; install once, `flowbook` picks them up |
| Custom Streamlit | Add `flowbook my-ui` via entry point, or run `streamlit run ...` directly |
