"""Offline evidence safety and provenance regressions; no network."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "sf079_evidence.py"
spec = importlib.util.spec_from_file_location("sf079_evidence", SCRIPT)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
SHA = "a" * 40


class EvidenceTests(unittest.TestCase):
    def fixture(self):
        return harness.build_evidence(
            {"endpoint": "synthetic://history", "method": "POST",
             "parameters": {"interval": 1, "provider_instrument_token": "16669"}},
            {"status_code": 200, "row_count": 0},
            observed_at="2026-10-14T00:00:00Z", fork_sha=SHA,
            policy_status="approved",
        )

    def test_allowlisted_instrument_identity_preserved(self):
        evidence = self.fixture()
        self.assertEqual(evidence["request"]["parameters"]["provider_instrument_token"], "16669")
        self.assertNotIn("body", evidence["response"])

    def test_secret_bearing_url_and_payload_are_rejected_before_write(self):
        base = {"method": "POST", "parameters": {"interval": 1}}
        with tempfile.TemporaryDirectory() as directory:
            for endpoint in ("https://example.com/history?api_key=secret123",
                             "https://user:password@example.com/history",
                             "https://example.com/secret123"):
                with self.assertRaises(ValueError):
                    harness.build_evidence(
                        {**base, "endpoint": endpoint}, {"status_code": 200},
                        observed_at="2026-10-14T00:00:00Z", fork_sha=SHA,
                        policy_status="approved")
            with self.assertRaises(ValueError):
                harness.build_evidence(
                    {**base, "endpoint": "synthetic://history",
                     "headers": {"Authorization": "secret"}},
                    {"status_code": 200}, observed_at="2026-10-14T00:00:00Z",
                    fork_sha=SHA, policy_status="approved")
            with self.assertRaises(ValueError):
                harness.build_evidence(
                    {**base, "endpoint": "synthetic://history"},
                    {"status_code": 200, "body": {"notes": "password=secret"}},
                    observed_at="2026-10-14T00:00:00Z", fork_sha=SHA,
                    policy_status="approved")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_sha_manifest_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = harness.write_snapshot(Path(directory), self.fixture())
            self.assertTrue(harness.verify_snapshot(path))
            self.assertEqual(harness.write_snapshot(Path(directory), self.fixture()), path)
            (path / "evidence.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                harness.verify_snapshot(path)
            with self.assertRaises(FileExistsError):
                harness.write_snapshot(Path(directory), self.fixture())

    def test_python_optimized_mode_cannot_bypass_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = harness.write_snapshot(Path(directory), self.fixture())
            (path / "evidence.json").write_text("{}", encoding="utf-8")
            command = [sys.executable, "-O", str(SCRIPT), "verify", "--snapshot", str(path)]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)

    def test_p0_is_repository_anchored_across_working_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "p0"], cwd=directory,
                capture_output=True, text=True, check=True)
            record = json.loads(result.stdout)
            self.assertEqual(record["fork_path"], str(SCRIPT.parents[1]))
            self.assertEqual(record["fork_sha"], harness.git_revision())
            self.assertEqual(len(record["fork_sha"]), 40)

    def test_source_use_gate_and_naive_time(self):
        request = {"method": "POST", "endpoint": "synthetic://history",
                   "parameters": {"interval": 1}}
        response = {"status_code": 200}
        with self.assertRaises(PermissionError):
            harness.build_evidence(request, response,
                observed_at="2026-10-14T00:00:00Z", fork_sha=SHA,
                policy_status="pending")
        with self.assertRaises(ValueError):
            harness.build_evidence(request, response,
                observed_at="2026-10-14T00:00:00", fork_sha=SHA,
                policy_status="approved")


if __name__ == "__main__":
    unittest.main()
