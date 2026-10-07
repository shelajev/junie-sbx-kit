#!/bin/bash
set -euo pipefail
mkdir -p /home/agent/.junie /home/agent/.local/share/junie
chown agent:agent /home/agent/.junie /home/agent/.local/share/junie
# sbx v0.46.0-rc5 writes the kit profile beside the workspace. Junie discovers
# global instructions in ~/.junie, so keep a managed reference there. Preserve
# existing personal instructions and replace only this kit's own section.
profile=/home/agent/.junie/AGENTS.md
kit_profile="$(dirname "${WORKSPACE_DIR:-/home/agent/workspace}")/AGENTS.md"
temporary="$(mktemp)"
trap 'rm -f "$temporary"' EXIT
if [[ -f "$profile" ]]; then
  awk '/^<!-- BEGIN JUNIE KIT -->$/{skip=1;next} /^<!-- END JUNIE KIT -->$/{skip=0;next} !skip' \
    "$profile" > "$temporary"
fi
printf '\n<!-- BEGIN JUNIE KIT -->\nRead the sandbox runtime and kit instructions in `%s`.\n<!-- END JUNIE KIT -->\n' \
  "$kit_profile" >> "$temporary"
install -o agent -g agent -m 0644 "$temporary" "$profile"
# Java ships its own trust store and does not use curl's system CA bundle.
# Refresh the per-sandbox CA on each boot, including certificate rotation.
proxy_ca=/usr/local/share/ca-certificates/proxy-ca.crt
if [[ -f "$proxy_ca" ]]; then
  keytool=/opt/junie/junie-app/lib/runtime/bin/keytool
  truststore=/opt/junie/junie-app/lib/runtime/lib/security/cacerts
  "$keytool" -delete -alias docker-sandbox-proxy \
    -keystore "$truststore" -storepass changeit >/dev/null 2>&1 || true
  "$keytool" -importcert -noprompt -alias docker-sandbox-proxy \
    -file "$proxy_ca" -keystore "$truststore" -storepass changeit
fi
