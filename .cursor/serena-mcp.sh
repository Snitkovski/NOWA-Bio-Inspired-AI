#!/usr/bin/env bash
# Stdio entrypoint for Serena MCP. Uses absolute paths so Cloud Agent stdio MCP
# (dashboard config) does not depend on PATH or shell rc files.
set -euo pipefail

SERENA_BIN="${SERENA_BIN:-/usr/local/bin/serena}"
PROJECT_ROOT="${SERENA_PROJECT_ROOT:-/workspace}"

if [[ ! -x "${SERENA_BIN}" ]]; then
  echo "serena-mcp: ${SERENA_BIN} not found or not executable." >&2
  echo "Run the Cloud Agent environment install (bash .cursor/install.sh) and trigger a new Build." >&2
  exit 127
fi

exec "${SERENA_BIN}" start-mcp-server \
  --context ide \
  --agent-interface tools \
  --project "${PROJECT_ROOT}"
