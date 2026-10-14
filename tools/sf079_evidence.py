"""Offline-only SF-079 qualification evidence harness. Never performs HTTP requests."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from urllib.parse import urlsplit
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SECRET_KEYS = re.compile(r"cookie|authorization|password|secret|auth[_-]?token|api[_-]?key|session|credential|set-cookie", re.I)
SAFE_PARAMS = {"interval", "timeInterval", "chartType", "fromDate", "toDate", "symbol", "symbolType", "provider_instrument_token"}
SAFE_RESPONSE = {"status_code", "row_count"}
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_METHODS = {"GET", "POST"}
EVIDENCE_VERSION = "sf079-offline-evidence-v1"


def safe_request(request):
    """Allowlist structural fields; never persist arbitrary headers, URLs or values."""
    if set(request) - {"method", "endpoint", "parameters", "headers"}:
        raise ValueError("Unknown request field")
    endpoint = request.get("endpoint")
    if not isinstance(endpoint, str):
        raise ValueError("Endpoint must be a string")
    parsed = urlsplit(endpoint)
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError("Endpoint credentials, query and fragment are not allowed")
    if parsed.scheme not in {"https", "synthetic"} or not parsed.hostname:
        raise ValueError("Unsupported endpoint URL")
    params = request.get("parameters")
    if not isinstance(params, dict) or not params or set(params) - SAFE_PARAMS:
        raise ValueError("Unapproved request parameters")
    safe = {}
    for key, val in params.items():
        if key in {"interval", "timeInterval", "fromDate", "toDate"}:
            if type(val) is not int or val < 0:
                raise ValueError("Numerical parameter must be nonnegative integer")
        elif key in {"symbol", "symbolType", "chartType", "provider_instrument_token"}:
            if not isinstance(val, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", val):
                raise ValueError("Unsafe instrument/enum field")
        safe[key] = val
    # Headers are accepted only as an empty object; secrets must not be copied.
    if request.get("headers", {}) != {}:
        raise ValueError("Raw request headers cannot be retained")
    return {"method": request["method"], "endpoint": endpoint, "parameters": safe}


def safe_response(response):
    """Metadata only; never accept raw HTTP payload or arbitrary free text."""
    if set(response) - SAFE_RESPONSE:
        raise ValueError("Raw response body or unapproved metadata cannot be retained")
    status = response.get("status_code")
    count = response.get("row_count", 0)
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError("Invalid HTTP status")
    if type(count) is not int or count < 0:
        raise ValueError("Invalid row count")
    return {"status_code": status, "row_count": count}


def canonical_bytes(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode("utf-8")


def git_revision():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        raise RuntimeError("Fork Git revision unavailable")


def git_dirty():
    root = Path(__file__).resolve().parents[1]
    try:
        return bool(subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip())
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Fork worktree state unavailable") from exc


def build_evidence(request, response, *, observed_at, fork_sha, policy_status):
    """Accept caller-supplied offline fixtures only; no implicit data acquisition."""
    if policy_status != "approved":
        raise PermissionError("Source-use and local retention approval required before any real response capture")
    if request.get("method") not in ALLOWED_METHODS:
        raise ValueError("Invalid HTTP method")
    if not isinstance(fork_sha, str) or not SHA_PATTERN.fullmatch(fork_sha):
        raise ValueError("Fork revision must be a full 40-digit Git SHA")
    request = safe_request(request)
    response = safe_response(response)
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
        "request": request,
        "response": response,
        "limitations": ["Caller-provided offline snapshot; not a verified provider acquisition"],
    }


def write_snapshot(root, evidence):
    """Create a tamper-evident snapshot; filesystem writes are not immutable."""
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
    if (manifest.get("schema") != EVIDENCE_VERSION
            or manifest.get("evidence_file") != "evidence.json"
            or hashlib.sha256(data).hexdigest() != manifest.get("evidence_sha256")
            or path.name != manifest.get("evidence_sha256")
            or canonical_bytes(json.loads(data)) != data):
        raise ValueError("Evidence snapshot integrity verification failed")
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
                          "fork_path": str(Path(__file__).resolve().parents[1]),
                          "tracked_worktree_dirty": git_dirty(),
                          "source_use": "UNVERIFIED: no provider requests authorized"},
                         indent=2))
    elif args.mode == "dry-run":
        example = build_evidence(
            {"method": "POST", "endpoint": "synthetic://example", "parameters": {"interval": 1}},
            {"status_code": 200, "row_count": 0},
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
