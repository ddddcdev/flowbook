"""Streamlit UI runner with venv handling (separate venv for pandas<3 compatibility)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _find_uv() -> str:
    """Return uv executable path; exit with hint if not found."""
    uv = shutil.which("uv")
    if not uv:
        print(
            "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh",
            file=sys.stderr,
        )
        sys.exit(1)
    return uv


def _find_repo_root() -> Path:
    """Find repo root (where pyproject.toml or flowbook package lives).

    Prefer cwd when it has pyproject.toml (avoids .venv-ui in site-packages when
    flowbook is installed and cwd was wrong). Then search from __file__ up.
    """
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists():
        return cwd
    p = Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists():
            return parent
        if (
            (parent / "flowbook").is_dir()
            and (parent / "flowbook" / "extensions" / "ui").exists()
            and (parent / "pyproject.toml").exists()
        ):
            return parent
    return cwd


def run(venv_dir: str | Path = ".venv-ui", extra_args: list[str] | None = None) -> int:
    """Create .venv-ui if needed, install flowbook+streamlit, run Streamlit. Returns exit code."""
    repo = _find_repo_root()
    venv = Path(venv_dir)
    if not venv.is_absolute():
        venv = repo / venv

    def _ensure_deps() -> None:
        uv = _find_uv()
        venv_arg = str(venv)
        # st.dataframe(key=, on_select=, selection_mode=) requires streamlit>=1.35.0
        pkgs = ["streamlit>=1.35.0", "requests", "altair>=4,<5"]
        if sys.version_info >= (3, 13):
            pkgs.append("standard-imghdr")  # imghdr removed in 3.13
        if (repo / "pyproject.toml").exists():
            subprocess.run(
                [uv, "pip", "install", "--python", venv_arg] + pkgs,
                check=True,
                cwd=repo,
            )
            subprocess.run(
                [uv, "pip", "install", "--python", venv_arg, "-e", str(repo)],
                check=True,
                cwd=repo,
            )
        else:
            subprocess.run(
                [uv, "pip", "install", "--python", venv_arg, "flowbook[full]"] + pkgs,
                check=True,
                cwd=repo,
            )

    if not venv.exists():
        print(f"Creating {venv} (streamlit + requests)...")
        subprocess.run([_find_uv(), "venv", str(venv)], check=True, cwd=repo)
        _ensure_deps()
    else:
        streamlit_exe = (
            venv / "bin" / "streamlit" if os.name != "nt" else venv / "Scripts" / "streamlit.exe"
        )
        if not streamlit_exe.exists():
            print(f"Installing streamlit into {venv}...")
            _ensure_deps()

    streamlit_exe = (
        venv / "bin" / "streamlit" if os.name != "nt" else venv / "Scripts" / "streamlit.exe"
    )
    app_path = repo / "flowbook" / "extensions" / "ui" / "app.py"
    if not app_path.exists():
        # Installed case: avoid importing flowbook.extensions.ui.app (pulls streamlit/
        # requests which may not be in main venv). Use flowbook.__file__ instead.
        import flowbook

        app_path = Path(flowbook.__file__).resolve().parent / "extensions" / "ui" / "app.py"
        # Ensure flowbook is in venv (app imports flowbook; venv may have only streamlit)
        venv_py = venv / "bin" / "python" if os.name != "nt" else venv / "Scripts" / "python.exe"
        check = subprocess.run(
            [str(venv_py), "-c", "import flowbook"],
            capture_output=True,
        )
        if check.returncode != 0:
            _ensure_deps()
    args = [str(streamlit_exe), "run", str(app_path)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(args, cwd=repo).returncode
