#!/usr/bin/env bash
# Mikasa start (macOS / Linux):  ./start_mikasa.sh
cd "$(dirname "$0")" || exit 1
if ! command -v uv >/dev/null 2>&1; then
  echo "uv nahi mila. Pehle install karo: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
exec uv run --extra mikasa python -m mikasa "$@"
