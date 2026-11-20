#!/usr/bin/env bash
# Chunked test runner. The full suite can be SIGKILLed in one process on small hosts.
# Usage: scripts/test.sh [extra pytest args]
#   PYTHON=/opt/data/mcp-servers/venv/bin/python scripts/test.sh
set -euo pipefail
PY="${PYTHON:-python3}"
CHUNK="${CHUNK:-5}"
cd "$(dirname "$0")/.."
mapfile -t files < <(ls tests/test_*.py)
failed=0
for ((i = 0; i < ${#files[@]}; i += CHUNK)); do
  chunk=("${files[@]:i:CHUNK}")
  echo "== chunk $((i / CHUNK + 1)): ${chunk[*]}"
  if ! "$PY" -m pytest -q "${chunk[@]}" "$@"; then failed=1; fi
done
exit "$failed"
