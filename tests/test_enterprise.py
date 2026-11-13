import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient

from app.enterprise.api import create_app
from app.enterprise.auth import Principal
from app.enterprise.config import Settings
from app.enterprise.db import Database, documents
from app.enterprise.index import Index
from app.enterprise.runtime import Runtime, select_evidence
from app.enterprise.storage import ObjectStore


class Embedding:
    def encode(self, texts, **kwargs):
        return [[1.0, 0.2] for text in texts]


class Reranker:
    def predict(self, pairs):
        return [1.0 for pair in pairs]


class EnterpriseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(root=Path(self.temp.name), auth_mode="dev", dev_secret="x" * 40, verify_answers=False)
        self.db = Database(self.settings)
        self.objects = ObjectStore(self.settings)
        self.index = Index(self.settings, self.db, self.objects, Embedding(), Reranker())
        self.contexts = []
        def model(question, context):
            self.contexts.append(context)
            return "制度规定如下。[资料 1]"
        self.runtime = Runtime(self.settings, self.db, self.objects, self.index, model=model)
        self.client = TestClient(create_app(self.settings, self.runtime))
        self.admin = Principal("admin", "tenant-a", ("finance", "hr"), ("admin",))

    def tearDown(self):
        self.runtime.provider.shutdown()
        self.db.engine.dispose()
        self.temp.cleanup()

    def token(self, tenant="tenant-a", subject="user", groups=None, roles=None, expires=120):
        claims = dict(sub=subject, tenant_id=tenant, groups=groups or ["finance"], roles=roles or [],
            iss="enterprise-rag-dev", aud=self.settings.audience, iat=int(time.time()), exp=int(time.time()) + expires)
        return {"Authorization": "Bearer " + jwt.encode(claims, self.settings.dev_secret, algorithm="HS256")}

    def upload(self, text="finance confidential", groups=None, identity=None):
        return self.runtime.upload(self.admin, "policy", text.encode(), ".txt", groups or ["finance"], identity)

    def publish(self):
        return self.runtime.run_job(self.db.new_job(self.admin.tenant))

    def test_authentication_and_admin_boundaries(self):
        self.assertEqual(self.client.post("/api/v2/query", json={"question": "hi"}).status_code, 401)
        self.assertEqual(self.client.get("/api/v2/documents", headers=self.token(expires=-1)).status_code, 401)
        self.assertEqual(self.client.get("/metrics", headers=self.token()).status_code, 403)
        self.assertEqual(self.client.get("/metrics", headers=self.token(roles=["admin"])).status_code, 200)

    def test_cross_tenant_cannot_see_list_original_or_evidence(self):
        document = self.upload()
        self.publish()
        headers = self.token(tenant="tenant-b", roles=["admin"])
        self.assertEqual(self.client.get("/api/v2/documents", headers=headers).json(), [])
        self.assertEqual(self.client.get(f'/api/v2/documents/{document["id"]}/original', headers=headers).status_code, 404)
        response = self.client.post("/api/v2/query", headers=headers, json={"question": "finance"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], [])
        self.assertEqual(self.contexts, [])

    def test_acl_prefilters_both_retrieval_branches_and_model(self):
        allowed = self.upload("finance reimbursement")
        self.upload("secret HR salaries", ["hr"])
        self.publish()
        response = self.client.post("/api/v2/query", headers=self.token(), json={"question": "policy"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(allowed["id"], response.json()["sources"][0]["chunk_id"])
        self.assertNotIn("secret HR", self.contexts[0])

    def test_acl_revoke_invalidates_cache_history_and_original(self):
        doc = self.upload()
        self.publish()
        headers = self.token()
        payload = {"question": "policy", "session_id": "session-1"}
        self.assertEqual(self.client.post("/api/v2/query", headers=headers, json=payload).status_code, 200)
        self.assertEqual(len(self.client.get("/api/v2/sessions/session-1", headers=headers).json()["turns"]), 1)
        response = self.client.put(f'/api/v2/documents/{doc["id"]}/acl', headers=self.token(roles=["admin"]), json={"groups": ["hr"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post("/api/v2/query", headers=headers, json=payload).json()["sources"], [])
        self.assertEqual(self.client.get(f'/api/v2/documents/{doc["id"]}/original', headers=headers).status_code, 404)
        history = self.client.get("/api/v2/sessions/session-1", headers=headers).json()["turns"]
        self.assertTrue(all("无法回答" in turn["answer"] for turn in history))

    def test_version_publish_and_rollback_serve_matching_original(self):
        doc = self.upload("version one")
        first = self.publish()
        self.upload("version two", identity=doc["id"])
        second = self.publish()
        self.assertNotEqual(first, second)
        headers = self.token(roles=["admin"])
        self.assertEqual(self.client.get(f'/api/v2/documents/{doc["id"]}/original?release_id={first}', headers=headers).text, "version one")
        self.index.rollback(self.admin.tenant, first)
        self.assertEqual(self.db.release(self.admin.tenant)["id"], first)
        self.assertEqual(self.client.get(f'/api/v2/documents/{doc["id"]}/original', headers=headers).text, "version one")

    def test_failed_publication_keeps_old_release(self):
        self.upload()
        first = self.publish()
        with patch("app.enterprise.index.parse_bytes", side_effect=ValueError("bad input")):
            with self.assertRaises(ValueError):
                self.publish()
        self.assertEqual(self.db.release(self.admin.tenant)["id"], first)

    def test_delete_immediately_revokes_old_snapshot(self):
        doc = self.upload()
        self.publish()
        response = self.client.delete(f'/api/v2/documents/{doc["id"]}', headers=self.token(roles=["admin"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post("/api/v2/query", headers=self.token(), json={"question": "policy"}).json()["sources"], [])

    def test_deduplication_and_token_budget(self):
        record = {"text": "small evidence", "relative_path": "p.pdf", "page_start": 1, "page_end": 1}
        long = {**record, "text": "证据" * 3000}
        selected = select_evidence([record, record, long], 128)
        self.assertEqual(selected, [record])

    def test_bad_citations_and_judge_failure_are_not_cached(self):
        self.upload()
        self.publish()
        self.runtime.model = lambda **kwargs: "invented [资料 99]"
        self.assertEqual(self.client.post("/api/v2/query", headers=self.token(), json={"question": "policy"}).status_code, 502)
        self.runtime.model = lambda **kwargs: "answer [资料 1]"
        self.runtime.judge = lambda *args: False
        self.assertEqual(self.client.post("/api/v2/query", headers=self.token(), json={"question": "policy"}).status_code, 502)

    def test_upload_limits_and_object_path_traversal(self):
        with self.assertRaises(ValueError):
            self.objects.get("../../etc/passwd")
        response = self.client.post("/api/v2/documents", headers=self.token(roles=["editor"]),
            data={"title": "bad", "groups": '["finance"]'}, files={"file": ("x.exe", b"binary")})
        self.assertEqual(response.status_code, 415)

    def test_cache_hit_and_history_user_isolation(self):
        self.upload()
        self.publish()
        payload = {"question": "policy"}
        first = self.client.post("/api/v2/query", headers=self.token(), json=payload).json()
        second = self.client.post("/api/v2/query", headers=self.token(), json=payload).json()
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertNotEqual(first["request_id"], second["request_id"])
        self.client.post("/api/v2/query", headers=self.token(), json={**payload, "session_id": "s"})
        self.assertEqual(self.client.get("/api/v2/sessions/s", headers=self.token(subject="other")).json()["turns"], [])


if __name__ == "__main__":
    unittest.main()
