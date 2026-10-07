#!/bin/bash
set -euo pipefail
version="${1:?Junie build is required}"
case "${2:?Target architecture is required}" in
  amd64) platform=linux-amd64 ;;
  arm64) platform=linux-aarch64 ;;
  *) echo "Unsupported Junie architecture: $2" >&2; exit 1 ;;
esac
archive="junie-release-${version}-${platform}.zip"
checksum="$(awk -v archive="$archive" '$2 == archive {print $1}' /usr/local/lib/junie-kit/releases.sha256)"
[[ "$checksum" =~ ^[a-f0-9]{64}$ ]] || {
  echo "No unique pinned checksum for $archive; update releases.sha256 first." >&2
  exit 1
}
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
payload="/var/cache/junie/$archive"
if [[ ! -f "$payload" ]]; then
  payload="$scratch/$archive"
  curl --fail --show-error --location --retry 3 \
    "https://github.com/JetBrains/junie/releases/download/${version}/${archive}" \
    -o "$payload"
fi
printf '%s  %s\n' "$checksum" "$payload" | sha256sum --check --strict
mkdir -p /opt/junie
unzip -q "$payload" -d /opt/junie
test -x /opt/junie/junie-app/bin/junie
test -x /opt/junie/junie-app/lib/runtime/bin/keytool
chown -R root:root /opt/junie
