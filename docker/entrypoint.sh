#!/usr/bin/env bash
set -euo pipefail

# Ensure runtime directory for services that expect it.
if [[ -z "${XDG_RUNTIME_DIR:-}" ]]; then
  export XDG_RUNTIME_DIR="/tmp/runtime-root"
  mkdir -p "$XDG_RUNTIME_DIR"
  chmod 700 "$XDG_RUNTIME_DIR"
fi

mkdir -p /var/log/supervisor /var/run/supervisor

cd /opt/fragment

exec "$@"
