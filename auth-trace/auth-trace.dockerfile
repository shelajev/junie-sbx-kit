FROM scratch
COPY scripts/metadata.py /usr/local/lib/junie-auth-trace/metadata.py
COPY --chmod=0755 scripts/start.sh /usr/local/lib/junie-auth-trace/start.sh
