#!/bin/bash
set -euo pipefail
# Execute the packaged launcher directly. The managed updater shim is unnecessary
# in an immutable kit; its payload and bundled JVM remain together under /opt.
export EJ_RUNNER_PWD="${EJ_RUNNER_PWD:-$PWD}"
export JUNIE_DATA="${JUNIE_DATA:-$HOME/.local/share/junie}"
[[ -n "${JUNIE_MODEL:-}" ]] || unset JUNIE_MODEL
exec /opt/junie/junie-app/bin/junie \
  --skip-update-check --skill-location /opt/junie-skills "$@"
