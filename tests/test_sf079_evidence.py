"""Offline P0 / SHA-256 / sanitization regressions; no network."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "sf079_evidence.py"
spec = importlib.util.spec_from_file_location("sf079_evidence", SCRIPT)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class EvidenceTests(unittest.TestCase):
    def fixture(self):
        return harness.build_evidence(
            {"endpoint": "synthetic://history", "method": "POST",
             "parameters": {"interval": 1, "token": "sensitive"},
             "headers": {"Cookie": "cookie-value"}},
            {"status_code": 200, "body": {"rows": [{"time": 123}],
                                           "nested": {"Authorization": "sensitive"}}},
            observed_at="2026-10-14T00:00:00Z", fork_sha="abc123",
            policy_status="approved",
        )

    def test_redaction_at_all_depths(self):
        evidence = self.fixture()
        serialized = json.dumps(evidence)
        for sensitive in ("cookie-value", "sensitive"):
            self.assertNotIn(sensitive, serialized)
        self.assertEqual(evidence["request"]["parameters"]["token"], "[REDACTED]")
        self.assertEqual(evidence["response"]["body"]["nested"]["Authorization"], "[REDACTED]")

    def test_immutable_hash_manifest_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = harness.write_snapshot(Path(directory), self.fixture())
            self.assertTrue(harness.verify_snapshot(path))
            self.assertEqual(harness.write_snapshot(Path(directory), self.fixture()), path)
            (path / "evidence.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(AssertionError):
                harness.verify_snapshot(path)
            with self.assertRaises(FileExistsError):
                harness.write_snapshot(Path(directory), self.fixture())

    def test_source_use_checkpoint_is_fail_closed(self):
        with self.assertRaises(PermissionError):
            harness.build_evidence(
                {"endpoint": "synthetic://history", "method": "POST",
                 "parameters": {"interval": 1}},
                {"status_code": 200, "body": {}},
                observed_at="2026-10-14T00:00:00Z", fork_sha="abc123",
                policy_status="pending",
            )

    def test_request_and_response_mandatory(self):
        with self.assertRaises(ValueError):
            harness.build_evidence(
                {"endpoint": "synthetic://history", "method": "POST"},
                {"status_code": 200, "body": {}},
                observed_at="2026-10-14T00:00:00Z", fork_sha="abc123",
                policy_status="approved",
            )


if __name__ == "__main__":
    unittest.main()
