"""Offline regression tests for DATA-002's opt-in synchronous HTTP transport."""
import os
import unittest
from unittest.mock import patch

from nsemine.bin import scraper


class SyncTransportTests(unittest.TestCase):
    def tearDown(self):
        session = getattr(scraper._SESSION_LOCAL, "session", None)
        if session is not None:
            session.close()
        scraper._SESSION_LOCAL.session = None
        scraper._SESSION_LOCAL.backend = None
        scraper._SESSION_LOCAL.seeded = False

    def test_requests_backend_has_tls_verification_enabled(self):
        with patch.dict(os.environ, {scraper.SYNC_HTTP_TRANSPORT_ENV: "requests"}):
            session = scraper._get_sync_session(force_new=True)
            self.assertTrue(session.verify)
            self.assertEqual(type(session).__module__.split(".")[0], "requests")

    def test_backend_change_discards_existing_session(self):
        with patch.dict(os.environ, {scraper.SYNC_HTTP_TRANSPORT_ENV: "requests"}):
            first = scraper._get_sync_session(force_new=True)
        with patch.dict(os.environ, {scraper.SYNC_HTTP_TRANSPORT_ENV: "curl_cffi"}):
            second = scraper._get_sync_session()
            self.assertIsNot(first, second)
            self.assertEqual(scraper._SESSION_LOCAL.backend, "curl_cffi")

    def test_invalid_backend_rejected(self):
        with patch.dict(os.environ, {scraper.SYNC_HTTP_TRANSPORT_ENV: "unknown"}):
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                scraper._get_sync_session(force_new=True)

    def test_transport_defaults_to_upstream(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(scraper._sync_transport_backend(), "curl_cffi")


if __name__ == "__main__":
    unittest.main()
