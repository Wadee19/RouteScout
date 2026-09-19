#!/usr/bin/env bash
set -euo pipefail

choose_python() {
  for candidate in python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(choose_python || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  cat <<'EOF'
RouteScout development requires Python 3.11 or 3.12.

macOS:
  brew install python@3.12

Then rerun:
  bash scripts/setup_dev_env.sh
EOF
  exit 2
fi

echo "RouteScout release: $(grep '^version' pyproject.toml | head -1)"
echo "Using: $(${PYTHON_BIN} --version)"
rm -rf .venv
"${PYTHON_BIN}" -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

python -m ruff check src scripts tests
python scripts/static_check.py
pytest -q
python scripts/verify_frozen_results.py
python -m pip check
python -c "import routescout; print(routescout.__version__); print(routescout.__file__)"
