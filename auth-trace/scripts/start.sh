#!/bin/bash
set -euo pipefail
state=/home/agent/.junie/auth-trace
mkdir -p "$state/proxy"
chown -R agent:agent "$state"
chmod 0700 "$state" "$state/proxy"
upstream="${HTTPS_PROXY:-${HTTP_PROXY:-}}"
[[ -n "$upstream" ]] || { echo 'No sandbox upstream proxy is configured.' >&2; exit 1; }
case "$upstream" in
  http://127.0.0.1:8081|http://localhost:8081)
    upstream="$(cat "$state/upstream")" ;;
esac
printf '%s\n' "$upstream" > "$state/upstream"
chmod 0600 "$state/upstream"
running=false
if [[ -f "$state/pid" ]]; then
  pid="$(cat "$state/pid")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    command_line="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
    [[ "$command_line" != *mitmdump* || "$command_line" != *junie-auth-trace* ]] || running=true
  fi
fi
if [[ "$running" == false ]]; then
  # Quiet mode and /dev/null discard mitmproxy's own output. Only the addon
  # writes a log; no flow archive, console dump, or raw debug log is created.
  sudo -u agent env -i HOME=/home/agent PATH=/usr/bin:/bin \
    JUNIE_AUTH_TRACE_FILE="$state/events.jsonl" \
    nohup /opt/junie-auth-trace/bin/mitmdump --quiet --mode "upstream:$upstream" \
      --listen-host 127.0.0.1 --listen-port 8081 \
      --set "confdir=$state/proxy" \
      --set ssl_verify_upstream_trusted_ca=/etc/ssl/certs/ca-certificates.crt \
      --scripts /usr/local/lib/junie-auth-trace/metadata.py \
      >/dev/null 2>&1 &
  printf '%s\n' "$!" > "$state/pid"
fi
for attempt in {1..30}; do
  if [[ -f "$state/proxy/mitmproxy-ca-cert.pem" ]] && \
      (echo >/dev/tcp/127.0.0.1/8081) 2>/dev/null; then
    break
  fi
  [[ "$attempt" != 30 ]] || { echo 'Authentication trace proxy failed to start.' >&2; exit 1; }
  sleep 1
done
keytool=/opt/junie/junie-app/lib/runtime/bin/keytool
truststore=/opt/junie/junie-app/lib/runtime/lib/security/cacerts
"$keytool" -delete -alias junie-auth-trace -keystore "$truststore" \
  -storepass changeit >/dev/null 2>&1 || true
"$keytool" -importcert -noprompt -alias junie-auth-trace \
  -file "$state/proxy/mitmproxy-ca-cert.pem" -keystore "$truststore" -storepass changeit
# Preserve the runtime's persistent environment and replace only our block.
environment=/etc/sandbox-persistent.sh
temporary="$(mktemp)"
awk '/^# BEGIN JUNIE AUTH TRACE$/{skip=1;next} /^# END JUNIE AUTH TRACE$/{skip=0;next} !skip' \
  "$environment" > "$temporary"
cat >> "$temporary" <<'ENV'
# BEGIN JUNIE AUTH TRACE
export HTTP_PROXY=http://127.0.0.1:8081
export HTTPS_PROXY=http://127.0.0.1:8081
export http_proxy=http://127.0.0.1:8081
export https_proxy=http://127.0.0.1:8081
# END JUNIE AUTH TRACE
ENV
cat "$temporary" > "$environment"
rm -f "$temporary"
