#!/usr/bin/env bash
# Install flowbook from PyPI into a temporary venv and run --version + doctor.
# Does not touch your project venv.
# Usage: ./scripts/verify_pypi_install.sh [version] [full]
#   version: e.g. 0.1.0a1 (default)
#   full: if set (e.g. "full"), also test flowbook[full] (slower).
# Example: ./scripts/verify_pypi_install.sh 0.1.0a1
# Example: ./scripts/verify_pypi_install.sh 0.1.0a1 full
set -euo pipefail
VERSION="${1:-0.1.0a1}"
RUN_FULL="${2:-}"
VENV_DIR="${VENV_DIR:-.venv-pypi-verify}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/.."
REPO_ROOT="$(pwd)"

echo "Creating temporary venv: ${REPO_ROOT}/${VENV_DIR}"
rm -rf "${VENV_DIR}"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install -q --upgrade pip

echo "=== Core: flowbook==${VERSION} ==="
"${VENV_DIR}/bin/pip" install -q "flowbook==${VERSION}"
echo "flowbook --version"
"${VENV_DIR}/bin/flowbook" --version
echo "flowbook doctor"
"${VENV_DIR}/bin/flowbook" doctor || true

if [ -n "${RUN_FULL}" ]; then
  echo ""
  echo "=== [full] extras: flowbook[full]==${VERSION} ==="
  "${VENV_DIR}/bin/pip" install -q "flowbook[full]==${VERSION}"
  echo "flowbook --version"
  "${VENV_DIR}/bin/flowbook" --version
  echo "flowbook doctor"
  "${VENV_DIR}/bin/flowbook" doctor || true
fi

echo ""
echo "Removing temporary venv..."
rm -rf "${VENV_DIR}"
if [ -n "${RUN_FULL}" ]; then
  echo "Verify OK (PyPI flowbook==${VERSION}, core + [full])."
else
  echo "Verify OK (PyPI flowbook==${VERSION}). Use second arg 'full' to test [full] extras."
fi
