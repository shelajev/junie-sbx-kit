"""mitmproxy addon: write an allowlisted metadata record, never a raw flow."""

import json
import os
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

SAFE_SEGMENTS = frozenset(
    "api auth oauth oauth2 v1 v2 v3 user me users models model tokens token "
    "refresh reset test license licenses userinfo user-info login device code "
    "authorize authorization callback oidc .well-known openid-configuration "
    "cli sessions poll status profile account subscriptions subscription usage "
    "entitlements chat completions responses search extract llm rest permanenttokens "
    "ide organization org".split()
)
SAFE_HOSTS = frozenset((
    "ingrazzio-cloud-prod.labs.jb.gg", "api.jetbrains.ai", "api.jetbrains.cloud",
    "auth.grazie.ai", "account.jetbrains.com", "oauth.account.jetbrains.com",
    "api.app.prod.grazie.aws.intellij.net", "junie.jetbrains.com",
))
SAFE_FIELDS = frozenset(
    "grant_type code code_verifier code_challenge code_challenge_method client_id "
    "redirect_uri refresh_token device_code response_type scope state "
    "access_token id_token token_type expires_in user_code verification_uri "
    "verification_uri_complete interval error".split()
)
SAFE_GRANTS = frozenset(
    ("authorization_code", "refresh_token", "client_credentials",
     "urn:ietf:params:oauth:grant-type:device_code")
)


def describe(flow):
    request = flow.request
    url = urlsplit(request.url)
    segments = url.path.split("/")
    path = "/".join(segment if not segment or segment in SAFE_SEGMENTS
                    else "[redacted]" for segment in segments)
    response = flow.response
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "method": request.method if request.method in
                  {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
                  else "[redacted]",
        "host": request.host if request.host in SAFE_HOSTS else "[redacted]",
        "port": request.port,
        "path": path,
        "query_fields": sorted(SAFE_FIELDS.intersection(parse_qs(url.query))),
        "status": response.status_code if response is not None else None,
        "authorization_present": bool(request.headers.get("authorization")),
    }
    authorization = request.headers.get("authorization", "")
    prefix = authorization.split(" ", 1)[0].lower()
    record["authorization_scheme"] = prefix if prefix in {"bearer", "basic"} else (
        "opaque" if authorization else "none")
    # Inspect only OAuth-shaped messages, and retain recognized field names.
    # Never serialize a body or an arbitrary error message.
    if any(segment in {"oauth", "oauth2", "auth"} for segment in segments):
        if "application/x-www-form-urlencoded" in request.headers.get("content-type", ""):
            fields = parse_qs(request.get_text(strict=False) or "")
            record["request_fields"] = sorted(SAFE_FIELDS.intersection(fields))
            grant = fields.get("grant_type", [""])[0]
            if grant in SAFE_GRANTS:
                record["grant_type"] = grant
        if response is not None and "application/json" in response.headers.get("content-type", ""):
            try:
                payload = json.loads(response.get_text(strict=False) or "")
            except (ValueError, UnicodeError):
                payload = None
            if isinstance(payload, dict):
                record["response_fields"] = sorted(SAFE_FIELDS.intersection(payload))
    return record


class Metadata:
    def write(self, flow):
        record = describe(flow)
        destination = os.environ["JUNIE_AUTH_TRACE_FILE"]
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    def response(self, flow):
        self.write(flow)

    def error(self, flow):
        self.write(flow)


addons = [Metadata()]
