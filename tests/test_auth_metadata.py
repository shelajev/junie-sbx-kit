import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

source = Path(__file__).resolve().parents[1] / "auth-trace/scripts/metadata.py"
spec = importlib.util.spec_from_file_location("metadata", source)
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)


def message(headers, body):
    return SimpleNamespace(headers=headers, get_text=lambda strict=False: body)


class MetadataTests(unittest.TestCase):
    def test_oauth_protocol_without_secrets(self):
        request = message({"authorization": "Bearer secret-access-value",
                           "cookie": "session=secret-cookie-value",
                           "content-type": "application/x-www-form-urlencoded"},
                          "grant_type=authorization_code&code=secret-code-value&"
                          "code_verifier=secret-verifier-value&client_id=junie-cli")
        request.url = "https://oauth.account.jetbrains.com/oauth2/token?state=secret-state-value"
        request.host = "oauth.account.jetbrains.com"
        request.port = 443
        request.method = "POST"
        response = message({"content-type": "application/json"}, json.dumps({
            "access_token": "secret-access-value", "refresh_token": "secret-refresh-value",
            "id_token": "secret-id-value", "email": "private@example.com", "expires_in": 3600}))
        response.status_code = 200
        flow = SimpleNamespace(request=request, response=response)
        record = metadata.describe(flow)
        self.assertEqual(record["grant_type"], "authorization_code")
        self.assertEqual(record["status"], 200)
        self.assertEqual(record["authorization_scheme"], "bearer")
        self.assertEqual(record["response_fields"],
                         ["access_token", "expires_in", "id_token", "refresh_token"])
        self.assertEqual(record["path"], "/oauth2/token")
        self.assertNotIn("secret-", json.dumps(record))
        self.assertNotIn("private@example.com", json.dumps(record))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            os.environ["JUNIE_AUTH_TRACE_FILE"] = str(path)
            metadata.Metadata().response(flow)
            self.assertNotIn("secret-", path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_unrecognized_paths_hosts_and_values_are_redacted(self):
        request = message({"authorization": "secret-opaque-token"}, "secret-body-value")
        request.url = "https://secret-host-value.example/auth/secret-path-value?code=secret-query-value"
        request.host = "secret-host-value.example"
        request.port = 443
        request.method = "GET"
        record = metadata.describe(SimpleNamespace(request=request, response=None))
        self.assertEqual(record["path"], "/auth/[redacted]")
        self.assertEqual(record["authorization_scheme"], "opaque")
        self.assertIsNone(record["status"])
        self.assertNotIn("secret-", json.dumps(record))

    def test_non_oauth_bodies_are_never_read(self):
        def forbidden(**kwargs):
            self.fail("A non-OAuth body was read")
        request = SimpleNamespace(
            headers={}, url="https://ingrazzio-cloud-prod.labs.jb.gg/chat",
            host="ingrazzio-cloud-prod.labs.jb.gg", port=443, method="POST",
            get_text=forbidden)
        response = SimpleNamespace(headers={"content-type": "application/json"},
                                   status_code=200, get_text=forbidden)
        self.assertEqual(metadata.describe(SimpleNamespace(
            request=request, response=response))["status"], 200)


if __name__ == "__main__":
    unittest.main()
