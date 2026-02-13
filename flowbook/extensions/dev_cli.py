"""
Dev CLI (Typer/Rich). Requires the dev extra: pip install "flowbook[dev]".
"""

from __future__ import annotations

import json
import os
import re
import sys
from urllib.parse import quote

try:
    import typer
    from typer import Context
except ImportError:
    typer = None  # type: ignore[assignment]
    Context = None  # type: ignore[assignment]


def _sanitize_filename(key: str) -> str:
    """Derive a safe filename from artifact key (no path, no bad chars)."""
    base = key.replace("/", "_").replace("\\", "_")
    base = re.sub(r'[<>:"|?*]', "_", base)
    return base or "artifact"


def main() -> None:
    if typer is None:
        print(
            'flowbook-dev requires the dev extra. Install with: pip install "flowbook[dev]"',
            file=sys.stderr,
        )
        sys.exit(1)
    assert typer is not None  # narrow for type checker
    assert Context is not None

    import flowbook

    t = typer
    app = t.Typer(
        name="flowbook-dev",
        help="Development CLI for flowbook (Typer/Rich).",
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

    # ---- artifacts (API) ----
    default_base = os.environ.get("FLOWBOOK_API_URL", "http://127.0.0.1:8000")

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

    app()


if __name__ == "__main__":
    main()
