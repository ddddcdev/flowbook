"""
flowbook extended CLI (Typer/Rich). Loaded by flowbook when flowbook[dev] is installed.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from typer import Typer

try:
    import typer
    from typer import Context
except ImportError:
    typer = None  # type: ignore[assignment]
    Context = None  # type: ignore[assignment]


def register_cli(app: Typer) -> None:
    """Register flowbook's built-in CLI commands. Called via flowbook.cli entry point."""
    if typer is None:
        return
    t = typer

    default_base = os.environ.get("FLOWBOOK_API_URL", "http://127.0.0.1:8000")

    # ---- db ----
    db_app = t.Typer(help="DB operations: reset, seed configs, seed defaults, seed artifact.")

    @db_app.command("reset")
    def db_reset(
        config_dir: str = t.Option(
            "configs", "--config-dir", "-C", help="Config directory to seed from"
        ),
    ) -> None:
        """Truncate artifacts and configs, then seed from config dir. Needs FLOWBOOK_DB_RESET=1."""
        from flowbook.extensions.cli.db import reset_db

        code = reset_db(config_dir)
        raise t.Exit(code)

    @db_app.command("seed")
    def db_seed(
        config_dir: str = t.Option("configs", "--config-dir", "-C", help="Config directory"),
    ) -> None:
        """Seed Postgres config store from JSON files in config dir."""
        from flowbook.extensions.cli.db import seed_configs_from_dir

        code = seed_configs_from_dir(config_dir)
        raise t.Exit(code)

    @db_app.command("seed-default")
    def db_seed_default() -> None:
        """Seed hardcoded InputProfile and PlanTemplates for API smoke test."""
        from flowbook.extensions.cli.db import seed_config_for_api

        code = seed_config_for_api()
        raise t.Exit(code)

    @db_app.command("seed-artifact")
    def db_seed_artifact() -> None:
        """Seed one smoke-test artifact for flowbook artifacts list."""
        from flowbook.extensions.cli.db import seed_one_artifact

        code = seed_one_artifact()
        raise t.Exit(code)

    app.add_typer(db_app, name="db")

    # ---- hands-on ----
    @app.command("hands-on")
    def hands_on(
        base_url: str = t.Option(
            default_base,
            "--base-url",
            envvar="FLOWBOOK_API_URL",
            help="API base URL",
        ),
        fixture: str = t.Option(
            "tests/fixtures/excel/test_detect_region_input.xlsx",
            "--fixture",
            "-f",
            help="Fixture Excel path",
        ),
        config_dir: str = t.Option(
            "configs", "--config-dir", "-C", help="Config directory for init"
        ),
        no_interactive: bool = t.Option(False, "--no-interactive", help="Skip prompts"),
    ) -> None:
        """Run hands-on flow: Health -> Inspect -> Import -> Artifacts -> Export -> Download."""
        from flowbook.extensions.cli.hands_on import run as run_hands_on

        code = run_hands_on(
            base_url=base_url,
            fixture_path=fixture,
            config_dir=config_dir,
            interactive=not no_interactive,
        )
        raise t.Exit(code)

    # ---- fixture ----
    fixture_app = t.Typer(help="Fixture generation for hands-on / e2e.")

    @fixture_app.command("generate")
    def fixture_generate(
        output: str = t.Option(
            "tests/fixtures/excel",
            "--output",
            "-o",
            help="Output directory for generated fixture",
        ),
    ) -> None:
        """Generate test_detect_region_input.xlsx for hands-on / e2e."""
        from flowbook.extensions.cli.fixture import generate as gen_fixture

        try:
            out_path = gen_fixture(output)
            t.echo(f"Wrote {out_path}")
        except ImportError as e:
            t.echo(str(e), err=True)
            raise t.Exit(1) from e

    app.add_typer(fixture_app, name="fixture")

    # ---- streamlit ----
    _streamlit_extra = t.Argument(default=None, help="Extra args passed to streamlit run")

    @app.command("streamlit")
    def streamlit_cmd(
        venv_dir: str = t.Option(
            ".venv-ui", "--venv", help="Venv for Streamlit (created if missing)"
        ),
        extra: list[str] = _streamlit_extra,
    ) -> None:
        """Run Streamlit UI in a separate venv (pandas version compatibility)."""
        from flowbook.extensions.cli.streamlit_runner import run as run_streamlit

        code = run_streamlit(venv_dir=venv_dir, extra_args=extra or [])
        raise t.Exit(code)

    # ---- artifacts (API) ----
    _add_artifacts_commands(app, default_base)


def _add_artifacts_commands(app: Typer, default_base: str) -> None:
    if typer is None:
        return
    t = typer
    artifacts_app = t.Typer(help="List, get, or preview artifacts from the flowbook API.")

    @artifacts_app.command("list")
    def artifacts_list(
        base_url: str = t.Option(
            default_base,
            "--base-url",
            envvar="FLOWBOOK_API_URL",
            help="API base URL.",
        ),
        run_id: str | None = t.Option(None, "--run-id", help="Filter by run ID (prefix)."),
        prefix: str | None = t.Option(None, "--prefix", help="Filter by key prefix."),
        limit: int | None = t.Option(None, "--limit", "-n", help="Max keys to show."),
    ) -> None:
        """GET /artifacts and show keys in a table."""
        import httpx
        from rich.table import Table

        p = prefix if prefix is not None else (f"{run_id}/" if run_id else None)
        params = {"prefix": p} if p is not None else {}
        url = f"{base_url.rstrip('/')}/artifacts"
        try:
            r = httpx.get(url, params=params, timeout=30.0)
            r.raise_for_status()
        except httpx.HTTPError as e:
            t.echo(f"Error: {e}", err=True)
            raise t.Exit(1) from e
        data = r.json()
        keys = data.get("keys", [])
        if limit is not None and limit > 0:
            keys = keys[:limit]
        table = Table(title="Artifacts")
        table.add_column("#", style="dim")
        table.add_column("key")
        for i, k in enumerate(keys, 1):
            table.add_row(str(i), k)
        from rich.console import Console

        Console().print(table)

    @artifacts_app.command("get")
    def artifacts_get(
        key: str = t.Argument(..., help="Artifact key."),
        output: str | None = t.Option(
            None, "-o", "--output", help="Output path; default: cwd, name from key."
        ),
        base_url: str = t.Option(
            default_base,
            "--base-url",
            envvar="FLOWBOOK_API_URL",
            help="API base URL.",
        ),
    ) -> None:
        """Download artifact to a file. Never prints binary to stdout."""
        import httpx

        path_enc = quote(key, safe="/")
        url = f"{base_url.rstrip('/')}/artifacts/{path_enc}/raw"
        try:
            r = httpx.get(url, timeout=60.0)
            r.raise_for_status()
        except httpx.HTTPError as e:
            t.echo(f"Error: {e}", err=True)
            raise t.Exit(1) from e
        path = output or os.path.join(os.getcwd(), _sanitize_filename(key))
        path = os.path.abspath(path)
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "wb") as f:
            f.write(r.content)
        t.echo(f"Saved to {path}")

    @artifacts_app.command("head")
    def artifacts_head(
        key: str = t.Argument(..., help="Artifact key."),
        n: int = t.Option(20, "--n", "-n", help="Number of lines (for CSV/text)."),
        base_url: str = t.Option(
            default_base,
            "--base-url",
            envvar="FLOWBOOK_API_URL",
            help="API base URL.",
        ),
    ) -> None:
        """Preview JSON/CSV artifact; show 'binary; use get' for others."""
        import httpx

        path_enc = quote(key, safe="/")
        url = f"{base_url.rstrip('/')}/artifacts/{path_enc}/raw"
        try:
            r = httpx.get(url, timeout=30.0)
            r.raise_for_status()
        except httpx.HTTPError as e:
            t.echo(f"Error: {e}", err=True)
            raise t.Exit(1) from e
        ct = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
        body = r.content
        if ct == "application/json":
            try:
                obj = json.loads(body.decode("utf-8"))
                out = json.dumps(obj, indent=2, ensure_ascii=False)
                lines = out.splitlines()
                for line in lines[:n]:
                    print(line)
                if len(lines) > n:
                    print(f"... ({len(lines) - n} more lines)")
            except Exception:
                t.echo("binary; use get", err=True)
                raise t.Exit(1) from None
        elif "csv" in ct or key.lower().endswith(".csv"):
            try:
                text = body.decode("utf-8")
                lines = text.splitlines()
                for line in lines[:n]:
                    print(line)
                if len(lines) > n:
                    print(f"... ({len(lines) - n} more lines)")
            except Exception:
                t.echo("binary; use get", err=True)
                raise t.Exit(1) from None
        else:
            t.echo("binary; use get")

    app.add_typer(artifacts_app, name="artifacts")

    # ---- verify (release; only when running from flowbook repo) ----
    if _is_flowbook_repo():
        verify_app = t.Typer(help="Release verification: PyPI install, wheel install.")

        @verify_app.command("pypi")
        def verify_pypi_cmd(
            version: str = t.Argument(
                None, help="Version to install (e.g. 0.1.0a2). Default: current __version__"
            ),
            full: bool = t.Option(False, "--full", help="Also test flowbook[full]"),
        ) -> None:
            """Install flowbook from PyPI into temp venv, run --version and doctor."""
            from flowbook.extensions.cli.verify import verify_pypi

            code = verify_pypi(version or "", full)
            raise t.Exit(code)

        @verify_app.command("wheel")
        def verify_wheel_cmd(
            wheel_dir: str = t.Option(
                "dist", "--wheel-dir", "-w", help="Directory with wheel (default: dist)"
            ),
            venv_dir: str = t.Option(
                ".venv-wheel-verify", "--venv", "-e", help="Temporary venv path"
            ),
        ) -> None:
            """Build wheel (if needed), install into temp venv, run --version and doctor."""
            from flowbook.extensions.cli.verify import verify_wheel

            code = verify_wheel(wheel_dir, venv_dir)
            raise t.Exit(code)

        app.add_typer(verify_app, name="verify")


def _is_flowbook_repo() -> bool:
    """True when flowbook is run from the development repo (editable install)."""
    import flowbook

    pkg_dir = Path(flowbook.__file__).resolve().parent
    repo_root = pkg_dir.parent
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        text = pyproject.read_text()
        return 'name = "flowbook"' in text or "name = 'flowbook'" in text
    except OSError:
        return False


def _sanitize_filename(key: str) -> str:
    """Derive a safe filename from artifact key (no path, no bad chars)."""
    base = key.replace("/", "_").replace("\\", "_")
    base = re.sub(r'[<>:"|?*]', "_", base)
    return base or "artifact"


def main() -> None:
    if typer is None:
        print(
            'flowbook extended CLI requires pip install "flowbook[dev]"',
            file=sys.stderr,
        )
        sys.exit(1)
    assert typer is not None
    assert Context is not None

    import flowbook
    from flowbook.extensions.cli.extensions import discover_cli_extensions

    t = typer
    app = t.Typer(
        name="flowbook",
        help="flowbook: db, hands-on, fixture, streamlit, artifacts.",
    )

    @app.callback(invoke_without_command=True)
    def global_callback(
        ctx: Context,  # pyright: ignore[reportInvalidTypeForm]
        version: bool = t.Option(False, "--version", "-v", help="Show version"),
    ) -> None:
        if version:
            print(flowbook.__version__)
            raise t.Exit()
        if ctx.invoked_subcommand is None:
            t.echo(ctx.get_help())

    @app.command()
    def doctor() -> None:
        """Check environment and suggest missing extras."""
        from flowbook.cli import _run_doctor

        code = _run_doctor()
        raise t.Exit(code)

    discover_cli_extensions(app)
    app()


if __name__ == "__main__":
    main()
