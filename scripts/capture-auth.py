"""Export validated, redacted authentication metadata from one sandbox."""

import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sandbox")
    parser.add_argument("--output", type=Path, default=Path(".local/oauth-trace.jsonl"))
    options = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "auth-trace/scripts/metadata.py"
    spec = importlib.util.spec_from_file_location("metadata", source)
    metadata = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metadata)
    result = subprocess.run([
        "sbx", "exec", options.sandbox, "cat",
        "/home/agent/.junie/auth-trace/events.jsonl"],
        capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("No trace is available; check that the auth-trace mixin is running.")
    records = []
    for line in result.stdout.splitlines():
        event = json.loads(line)
        if event.get("host") not in metadata.SAFE_HOSTS | {"[redacted]"}:
            raise SystemExit("Rejected a trace record containing an unrecognized host.")
        if event.get("method") not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "[redacted]"}:
            raise SystemExit("Rejected a trace record containing an unrecognized method.")
        path = event["path"]
        if any(part not in metadata.SAFE_SEGMENTS | {"", "[redacted]"} for part in path.split("/")):
            raise SystemExit("Rejected a trace record containing an unredacted path.")
        status = event.get("status")
        if status is not None and (type(status) is not int or not 100 <= status <= 599):
            raise SystemExit("Rejected an invalid HTTP status.")
        port = event["port"]
        if type(port) is not int or not 1 <= port <= 65535:
            raise SystemExit("Rejected an invalid port.")
        scheme = event["authorization_scheme"]
        if scheme not in {"bearer", "basic", "opaque", "none"}:
            raise SystemExit("Rejected an unrecognized authentication scheme.")
        record = {
            "time": datetime.fromisoformat(event["time"]).isoformat(),
            "host": event["host"], "port": port, "method": event["method"],
            "path": path, "status": status, "authorization_scheme": scheme,
            "authorization_present": event.get("authorization_present") is True,
        }
        for key in ("query_fields", "request_fields", "response_fields"):
            if key in event:
                record[key] = sorted(metadata.SAFE_FIELDS.intersection(event[key]))
        if event.get("grant_type") in metadata.SAFE_GRANTS:
            record["grant_type"] = event["grant_type"]
        records.append(record)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(options.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"Saved {len(records)} metadata events to {options.output.resolve()}")


if __name__ == "__main__":
    main()
