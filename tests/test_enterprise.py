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
        doc = self.upload()
        first = self.publish()
        # A new version that cannot be parsed: nothing new to publish, keep the old release.
        self.upload("finance confidential v2", identity=doc["id"])
        with patch("app.enterprise.index.parse_bytes", side_effect=ValueError("bad input")):
            with self.assertRaises(ValueError):
                self.publish()
        self.assertEqual(self.db.release(self.admin.tenant)["id"], first)

    def test_first_publication_with_only_bad_documents_fails(self):
        self.upload()
        with patch("app.enterprise.index.parse_bytes", side_effect=ValueError("bad input")):
            with self.assertRaises(ValueError):
                self.publish()
        self.assertIsNone(self.db.release(self.admin.tenant))

    def test_unparseable_new_version_keeps_serving_published_version(self):
        doc = self.upload("finance reimbursement")
        other = self.upload("hr leave rules", ["hr"])
        self.publish()
        self.upload("finance reimbursement v2", identity=doc["id"])
        self.upload("hr leave rules v2", ["hr"], identity=other["id"])
        real_parse = __import__("app.enterprise.index", fromlist=["parse_bytes"]).parse_bytes

        def flaky(data, suffix, mode="basic"):
            if b"finance" in data:
                raise ValueError("unreadable")
            return real_parse(data, suffix, mode)

        with patch("app.enterprise.index.parse_bytes", side_effect=flaky):
            self.publish()
        release = self.client.get("/api/v2/index/releases", headers=self.token(roles=["admin"])).json()["releases"][0]
        self.assertEqual(release["documents"], 2)
        self.assertEqual(release["failures"][0]["kept_version"], 1)
        listing = {item["id"]: item for item in self.client.get("/api/v2/documents", headers=self.token(roles=["admin"])).json()}
        self.assertEqual(listing[doc["id"]]["status"], "failed")
        self.assertEqual(listing[doc["id"]]["published_version"], 1)
        self.assertEqual(listing[other["id"]]["status"], "published")
        body = self.client.post("/api/v2/query", headers=self.token(), json={"question": "finance"}).json()
        self.assertIn(":1:", body["sources"][0]["chunk_id"])

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

    def test_bad_citations_and_judge_failure_are_withheld_and_not_cached(self):
        self.upload()
        self.publish()
        self.runtime.model = lambda **kwargs: "invented [资料 99]"
        for _ in range(2):
            response = self.client.post("/api/v2/query", headers=self.token(), json={"question": "policy"})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["verification"], "citation_invalid")
            self.assertEqual(body["sources"], [])
            self.assertNotIn("invented", body["answer"])
            self.assertFalse(body["cached"])
        self.runtime.model = lambda **kwargs: "answer [资料 1]"
        self.runtime.judge = lambda *args: False
        body = self.client.post("/api/v2/query", headers=self.token(), json={"question": "policy two"}).json()
        self.assertEqual(body["verification"], "judge_failed")
        self.assertEqual(body["status"], "refused")
        self.assertFalse(self.client.post("/api/v2/query", headers=self.token(), json={"question": "policy two"}).json()["cached"])

    def test_partial_verification_drops_only_unsupported_sentences(self):
        self.upload()
        self.publish()
        self.runtime.model = lambda **kwargs: "第一条有依据。[资料 1]\n第二条是编的。"

        class Judge:
            def assess(self, question, answer, records):
                return {"status": "partial", "unsupported": ["第二条是编的。"]}

        self.runtime.judge = Judge()
        body = self.client.post("/api/v2/query", headers=self.token(), json={"question": "policy"}).json()
        self.assertEqual(body["verification"], "judge_partial")
        self.assertIn("第一条有依据", body["answer"])
        self.assertNotIn("第二条是编的", body["answer"])
        self.assertEqual(body["unsupported_claims"], ["第二条是编的。"])
        self.assertEqual(len(body["sources"]), 1)

    def test_one_bad_document_does_not_block_publication(self):
        good = self.upload("finance reimbursement")
        bad = self.runtime.upload(self.admin, "broken", b"broken", ".txt", ["finance"], None, "broken-doc")
        real_parse = __import__("app.enterprise.index", fromlist=["parse_bytes"]).parse_bytes

        def flaky(data, suffix, mode="basic"):
            if data == b"broken":
                raise ValueError("unreadable")
            return real_parse(data, suffix, mode)

        with patch("app.enterprise.index.parse_bytes", side_effect=flaky):
            release_id = self.publish()
        listing = self.client.get("/api/v2/index/releases", headers=self.token(roles=["admin"])).json()
        current = listing["releases"][0]
        self.assertEqual(listing["active"], release_id)
        self.assertEqual(current["documents"], 1)
        self.assertEqual([item["document_id"] for item in current["failures"]], [bad["id"]])
        statuses = {item["id"]: item["status"] for item in self.client.get("/api/v2/documents", headers=self.token(roles=["admin"])).json()}
        self.assertEqual(statuses, {good["id"]: "published", bad["id"]: "failed"})

    def test_unchanged_documents_reuse_embeddings_and_old_releases_are_collected(self):
        calls = []

        class CountingEmbedding(Embedding):
            def encode(self, texts, **kwargs):
                calls.append(len(texts))
                return super().encode(texts, **kwargs)

        self.index._embedder = CountingEmbedding()
        self.settings.keep_releases = 2
        self.upload("finance reimbursement")
        self.publish()
        embedded_once = sum(calls)
        self.upload("hr leave rules", ["hr"])
        self.publish()
        # Only the new document is embedded (plus no re-embedding of the first one).
        self.assertEqual(sum(calls) - embedded_once, 1)
        self.publish()
        listing = self.client.get("/api/v2/index/releases", headers=self.token(roles=["admin"])).json()
        self.assertEqual(len(listing["releases"]), 2)
        self.assertEqual(listing["releases"][0]["reused"], 2)

    def test_follow_up_question_is_rewritten_for_retrieval(self):
        self.upload("finance reimbursement")
        self.publish()
        seen = []
        self.runtime.rewriter = lambda question, turns: seen.append((question, turns)) or "finance reimbursement rules"
        headers = self.token()
        self.client.post("/api/v2/query", headers=headers, json={"question": "policy", "session_id": "s1"})
        body = self.client.post("/api/v2/query", headers=headers, json={"question": "那它呢", "session_id": "s1"}).json()
        self.assertEqual(body["search_query"], "finance reimbursement rules")
        self.assertEqual(seen[-1][0], "那它呢")
        self.assertEqual(seen[-1][1][0], {"role": "user", "content": "policy"})

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
