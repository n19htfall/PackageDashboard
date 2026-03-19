#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS=()

cleanup() {
  local exit_code=${1:-0}
  trap - EXIT INT TERM

  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done

  wait >/dev/null 2>&1 || true
  exit "$exit_code"
}

trap 'cleanup $?' EXIT
trap 'cleanup 130' INT TERM

echo "Starting backend on http://127.0.0.1:19428 ..."
(
  cd "$ROOT_DIR/backend"
  exec poetry run pkgdash-api --reload
) &
PIDS+=($!)

echo "Starting frontend on http://127.0.0.1:19429 ..."
pnpm --dir "$ROOT_DIR/frontend" dev &
PIDS+=($!)

while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      wait "$pid"
      cleanup $?
    fi
  done
  sleep 1
done
