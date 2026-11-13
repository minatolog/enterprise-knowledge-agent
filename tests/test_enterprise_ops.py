import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.enterprise.auth import Auth
from app.enterprise.config import Settings
from app.enterprise.connectors import fetch_pages
from app.enterprise.db import Database
from app.enterprise.verification import EvidenceJudge


def script(name):
    location = Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EnterpriseOpsTests(unittest.TestCase):
    def test_oidc_rs256_issuer_audience_and_expiry(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        settings = Settings(issuer="https://identity.example/realm", jwks_url="https://identity.example/jwks")
        auth = Auth(settings)
        auth.jwks = Mock()
        auth.jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=key.public_key())
        claims = dict(sub="alice", tenant_id="a", groups=["finance"], roles=[], iss=settings.issuer,
            aud=settings.audience, iat=int(time.time()), exp=int(time.time()) + 60)
        token = jwt.encode(claims, key, algorithm="RS256")
        self.assertEqual(auth.verify("Bearer " + token).tenant, "a")
        for changed in ({"iss": "https://evil.example"}, {"aud": "wrong"}, {"exp": int(time.time()) - 1}):
            bad = jwt.encode({**claims, **changed}, key, algorithm="RS256")
            with self.assertRaises(HTTPException):
                auth.verify("Bearer " + bad)

    def test_connector_requires_explicit_https_allowlist(self):
        settings = Settings(auth_mode="dev", dev_secret="x" * 40, connector_hosts="wiki.example")
        for url in ("http://wiki.example/x", "https://evil.example/x", "https://user:pass@wiki.example/x", "https://wiki.example:8080/x"):
            with self.assertRaises(ValueError):
                fetch_pages(settings, url)

    def test_judge_fails_closed_on_invalid_json(self):
        client = Mock()
        for answer, expected in (("not json", False), ('{"supported": "true"}', False), ('{"supported": false}', False), ('{"supported": true}', True)):
            client.responses.create.return_value = SimpleNamespace(output_text=answer)
            with patch("llm.get_client", return_value=client):
                self.assertEqual(EvidenceJudge()("q", "answer [资料 1]", [{"text": "evidence"}]), expected)

    def test_backup_restore_and_tamper_detection(self):
        module = script("enterprise_backup")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(root=root / "state", auth_mode="dev", dev_secret="x" * 40)
            database = Database(settings)
            database.engine.dispose()
            module.backup(settings, root / "backup")
            self.assertEqual(module.restore(root / "backup", root / "restored"), "sqlite")
            self.assertTrue((root / "restored/metadata.sqlite3").exists())
            with self.assertRaises(ValueError):
                module.restore(root / "backup", root / "restored")
            (root / "backup/metadata.json").write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                module.restore(root / "backup", root / "tampered")

    def test_evaluation_does_not_invent_human_accuracy(self):
        module = script("enterprise_eval")
        row = dict(id="q1", question="q", answer="answer [资料 1]", evidence=[{"text": "evidence"}])
        result = module.evaluate([row], judge=lambda *args: True)
        self.assertIsNone(result["human_accuracy"])
        self.assertEqual(result["human_reviewed_count"], 0)
        self.assertTrue(result["results"][0]["judge_supported"])

    def test_publish_api_records_job_status_and_retry(self):
        from test_enterprise import EnterpriseTests
        fixture = EnterpriseTests()
        fixture.setUp()
        try:
            fixture.upload()
            headers = fixture.token(roles=["admin"])
            with patch("app.enterprise.index.parse_bytes", side_effect=ValueError("bad")):
                response = fixture.client.post("/api/v2/index/publish", headers=headers)
            identity = response.json()["job_id"]
            self.assertEqual(fixture.client.get("/api/v2/jobs/" + identity, headers=headers).json()["status"], "failed")
            fixture.client.post("/api/v2/jobs/" + identity + "/retry", headers=headers)
            self.assertEqual(fixture.client.get("/api/v2/jobs/" + identity, headers=headers).json()["status"], "succeeded")
        finally:
            fixture.tearDown()

    def test_connector_sync_is_idempotent(self):
        from test_enterprise import EnterpriseTests
        fixture = EnterpriseTests()
        fixture.setUp()
        try:
            rows = [{"external_id": "page-1", "title": "Wiki", "text": "company policy"}]
            with patch("app.enterprise.connectors.fetch_pages", return_value=rows):
                for _ in range(2):
                    result = fixture.client.post("/api/v2/connectors/sync", headers=fixture.token(roles=["admin"]),
                        json={"url": "https://wiki.example/page", "groups": ["finance"]})
                    self.assertEqual(result.status_code, 200, result.text)
            documents = fixture.client.get("/api/v2/documents", headers=fixture.token()).json()
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]["version"], 1)
        finally:
            fixture.tearDown()

    def test_request_spans_and_usage_metrics_do_not_record_evidence(self):
        from test_enterprise import EnterpriseTests
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        fixture = EnterpriseTests()
        fixture.setUp()
        try:
            exporter = InMemorySpanExporter()
            fixture.runtime.provider.add_span_processor(SimpleSpanProcessor(exporter))
            fixture.runtime.query(fixture.admin, "private question")
            spans = exporter.get_finished_spans()
            self.assertIn("rag.query", [span.name for span in spans])
            self.assertTrue(all(not span.attributes for span in spans))
            fixture.runtime.record_usage(SimpleNamespace(input_tokens=10, output_tokens=3))
            metrics = fixture.runtime.metrics().decode()
            self.assertIn('rag_model_tokens_total{direction="input"} 10.0', metrics)
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
