#!/usr/bin/env sh
set -eu

if command -v gh >/dev/null 2>&1; then
  if ! gh copilot --help >/dev/null 2>&1; then
    echo "[entrypoint] gh-copilot extension missing, attempting install..."
    if ! gh extension install github/gh-copilot >/tmp/gh-copilot-install.log 2>&1; then
      echo "[entrypoint] warning: unable to install gh-copilot extension"
      echo "[entrypoint] details:"
      cat /tmp/gh-copilot-install.log || true
    fi
  fi
fi

exec "$@"
