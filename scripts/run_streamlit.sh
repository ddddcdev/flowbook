#!/usr/bin/env bash
# Run Streamlit UI in a separate venv (streamlit requires pandas<3, flowbook uses pandas 3).
# Usage: ./scripts/run_streamlit.sh

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${REPO_ROOT}/.venv-ui"

if [[ ! -d "$VENV" ]]; then
  echo "Creating .venv-ui (streamlit + requests)..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -e "$REPO_ROOT" streamlit requests --quiet
fi

cd "$REPO_ROOT"
exec "$VENV/bin/streamlit" run flowbook/extensions/ui/app.py "$@"
