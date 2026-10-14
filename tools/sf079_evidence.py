"""Offline-only SF-079 qualification evidence harness. Never performs HTTP requests."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SECRET_KEYS = re.compile(r"cookie|authorization|password|secret|token|api[_-]?key|session|credential|set-cookie", re.I)
ALLOWED_METHODS = {"GET", "POST"}
EVIDENCE_VERSION = "sf079-offline-evidence-v1"


def scrub(value):
    """Conservatively redact sensitive keys at every depth; omit no evidence silently."""
    if isinstance(value, dict):
        return {str(k): ("[REDACTED]" if SECRET_KEYS.search(str(k)) else scrub(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError("Evidence must contain JSON primitives only")


def canonical_bytes(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode("utf-8")


def git_revision():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def build_evidence(request, response, *, observed_at, fork_sha, policy_status):
    """Accept caller-supplied offline fixtures only; no implicit data acquisition."""
    if policy_status != "approved":
        raise PermissionError("Source-use and local retention approval required before any real response capture")
    if request.get("method") not in ALLOWED_METHODS:
        raise ValueError("Invalid HTTP method")
    if not request.get("endpoint") or not request.get("parameters"):
        raise ValueError("Endpoint and transmitted parameters are required")
    if not response.get("status_code") or "body" not in response:
        raise ValueError("Response status_code and body are required")
    try:
        parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError("observed_at must be ISO8601") from exc
    return {
        "schema": EVIDENCE_VERSION,
        "observed_at": observed_at,
        "implementation_revision": fork_sha,
        "request": scrub(request),
        "response": scrub(response),
        "limitations": ["Caller-provided offline snapshot; not a verified provider acquisition"],
    }


def write_snapshot(root, evidence):
    """One immutable directory per semantic digest; refuse changes to existing artifacts."""
    data = canonical_bytes(evidence)
    digest = hashlib.sha256(data).hexdigest()
    target = root / digest
    root.mkdir(parents=True, exist_ok=True)
    try:
        target.mkdir()
    except FileExistsError:
        if not (target / "evidence.json").exists() or (target / "evidence.json").read_bytes() != data:
            raise FileExistsError("Existing evidence snapshot differs or is incomplete")
        verify_snapshot(target)
        return target
    try:
        with (target / "evidence.json").open("xb") as fh:
            fh.write(data)
        manifest = {"schema": EVIDENCE_VERSION, "evidence_sha256": digest,
                    "evidence_file": "evidence.json"}
        with (target / "manifest.json").open("xb") as fh:
            fh.write(canonical_bytes(manifest))
    except Exception:
        # Never claim a partial write is a valid immutable snapshot.
        raise
    return target


def verify_snapshot(path):
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    data = (path / "evidence.json").read_bytes()
    assert manifest["schema"] == EVIDENCE_VERSION
    assert manifest["evidence_file"] == "evidence.json"
    assert hashlib.sha256(data).hexdigest() == manifest["evidence_sha256"]
    assert path.name == manifest["evidence_sha256"]
    assert canonical_bytes(json.loads(data)) == data
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("p0", "dry-run", "verify"))
    parser.add_argument("--out", type=Path, default=Path("sf079-local-evidence"))
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.mode == "p0":
        print(json.dumps({"mode": "P0", "network": False, "fork_sha": git_revision(),
                          "python": sys.version.split()[0], "timezone": os.environ.get("TZ", "unset"),
                          "source_use": "UNVERIFIED: no provider requests authorized"},
                         indent=2))
    elif args.mode == "dry-run":
        example = build_evidence(
            {"method": "POST", "endpoint": "synthetic://example", "parameters": {"interval": 1},
             "headers": {"Authorization": "fixture-secret"}},
            {"status_code": 200, "body": {"rows": [], "token": "fixture-secret"}},
            observed_at="2026-10-14T00:00:00Z", fork_sha=git_revision(), policy_status="approved",
        )
        target = write_snapshot(args.out, example)
        verify_snapshot(target)
        print(f"Verified synthetic evidence: {target}")
    else:
        if not args.snapshot:
            parser.error("--snapshot is required for verify")
        verify_snapshot(args.snapshot)
        print("Snapshot verified")


if __name__ == "__main__":
    main()
