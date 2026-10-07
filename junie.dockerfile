# syntax=docker/dockerfile:1
# A pinned multi-platform base. Supply the complete sbx platform floor here.
FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
ARG JUNIE_VERSION
ARG TARGETARCH
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bash ca-certificates curl git jq libstdc++6 ripgrep sudo unzip \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 1000 --create-home --shell /bin/bash agent \
 && printf 'agent ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/agent \
 && chmod 0440 /etc/sudoers.d/agent \
 && mkdir -p /home/agent/workspace /home/agent/.junie \
      /home/agent/.local/share/junie /opt/junie-skills \
      /usr/local/share/ca-certificates \
 && chown -R agent:agent /home/agent \
 && touch /etc/sandbox-persistent.sh
COPY releases.sha256 /usr/local/lib/junie-kit/releases.sha256
COPY scripts/install.sh scripts/startup.sh /usr/local/lib/junie-kit/
RUN --mount=type=bind,source=.cache,target=/var/cache/junie,readonly \
    chmod 0755 /usr/local/lib/junie-kit/*.sh \
 && /usr/local/lib/junie-kit/install.sh "$JUNIE_VERSION" "$TARGETARCH"
COPY scripts/junie.sh /usr/local/bin/junie
RUN chmod 0755 /usr/local/bin/junie
ENV HOME=/home/agent \
    BASH_ENV=/etc/sandbox-persistent.sh \
    JUNIE_SKIP_UPDATE_CHECK=1 \
    JUNIE_SHARE_ANONYMOUS_STATISTICS=false \
    IS_SANDBOX=1
USER agent
WORKDIR /home/agent/workspace
# Enforce the provides claim using the installed executable, as its runtime user.
RUN actual="$(junie --version)" \
 && printf '%s\n' "$actual" \
 && case "$actual" in \
      *" (${JUNIE_VERSION})") ;; \
      *) echo "Installed Junie build does not match ${JUNIE_VERSION}" >&2; exit 1 ;; \
    esac
ENTRYPOINT ["junie", "--brave"]
