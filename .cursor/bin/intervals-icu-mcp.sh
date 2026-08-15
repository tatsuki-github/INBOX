#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

if ! command -v uvx >/dev/null 2>&1; then
  echo "uvx not found. Install uv first: https://github.com/astral-sh/uv" >&2
  exit 1
fi

exec uvx intervals-icu-mcp "$@"
