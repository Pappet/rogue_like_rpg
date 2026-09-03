#!/usr/bin/env bash
# Run a command with the project's Python interpreter.
#
# The pre-commit hooks used to hardcode `.venv/bin/python`, which silently
# fails for anyone whose environment lives somewhere else. Resolution order:
#
#   1. an activated virtualenv ($VIRTUAL_ENV) — what the developer chose
#   2. ./.venv — the layout the README assumes
#   3. whatever python is on PATH
#
# Usage: scripts/with-python.sh -m pytest tests/test_smoke.py -x -q
set -euo pipefail

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PY="$VIRTUAL_ENV/bin/python"
elif [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
else
    PY="$(command -v python3 || command -v python)"
fi

if [ -z "$PY" ]; then
    echo "with-python.sh: no Python interpreter found" >&2
    exit 1
fi

exec "$PY" "$@"
