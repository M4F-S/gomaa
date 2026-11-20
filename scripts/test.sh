#!/usr/bin/env bash
# Chunked test runner. The full suite can be SIGKILLed (OOM) in one process on small hosts,
# and two model-loading files in the same chunk can hit the same limit.
# Usage: scripts/test.sh [extra pytest args]
#   PYTHON=/opt/data/mcp-servers/venv/bin/python scripts/test.sh
set -uo pipefail
PY="${PYTHON:-python3}"
CHUNK="${CHUNK:-3}"
cd "$(dirname "$0")/.."
mapfile -t files < <(ls tests/test_*.py)
failed=0
for ((i = 0; i < ${#files[@]}; i += CHUNK)); do
  chunk=("${files[@]:i:CHUNK}")
  echo "== chunk $((i / CHUNK + 1)): ${chunk[*]}"
  "$PY" -m pytest -q "${chunk[@]}" "$@"
  rc=$?
  if [ "$rc" -eq 137 ]; then
    echo "!! chunk killed (137, likely OOM); retrying files individually"
    for f in "${chunk[@]}"; do
      "$PY" -m pytest -q "$f" "$@" || failed=1
    done
  elif [ "$rc" -ne 0 ]; then
    failed=1
  fi
done
exit "$failed"
