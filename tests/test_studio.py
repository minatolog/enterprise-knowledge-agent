"""Production frontend delivery, with no corpus or model access."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.api import create_app


class StudioDeliveryTests(unittest.TestCase):
    def test_built_studio_and_assets_use_same_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            studio = Path(directory)
            (studio / 'assets').mkdir()
            (studio / 'index.html').write_text('<html>Knowledge Studio<script src="/studio/assets/app.js"></script></html>')
            (studio / 'assets' / 'app.js').write_text('console.log("studio")')
            with patch('app.api._STUDIO_DIR', studio):
                client = TestClient(create_app())
                self.assertIn('Knowledge Studio', client.get('/').text)
                self.assertEqual(client.get('/studio/').status_code, 200)
                self.assertEqual(client.get('/studio/assets/app.js').status_code, 200)
                self.assertEqual(client.get('/studio/missing.js').status_code, 404)
                self.assertEqual(client.get('/health').json(), {'status': 'ok'})
                self.assertIn('id="query-form"', client.get('/legacy').text)

    def test_missing_build_preserves_original_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('app.api._STUDIO_DIR', Path(directory)):
                client = TestClient(create_app())
                self.assertIn('id="query-form"', client.get('/').text)
                self.assertEqual(client.get('/studio/').status_code, 404)
