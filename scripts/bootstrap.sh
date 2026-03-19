#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command poetry
require_command pnpm

echo "Installing backend dependencies with Poetry..."
(
  cd "$ROOT_DIR/backend"
  poetry install
)

echo "Installing frontend dependencies with pnpm..."
pnpm --dir "$ROOT_DIR/frontend" install

echo "Project dependencies are ready."
