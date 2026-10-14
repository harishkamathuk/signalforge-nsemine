# SF-079 Stage 2 — offline qualification evidence preparation

This folder's tool `tools/sf079_evidence.py` is **offline only**. It does not import the nsemine historical requester or initiate network access, and does not implement a SignalForge provider adapter. It supports P0 environment reporting and a synthetic sanitized evidence/manifest dry run. **It cannot certify live-source evidence or grant use permissions.**

Run from the fork checkout:

```bash
python tools/sf079_evidence.py p0
python tools/sf079_evidence.py dry-run --out /tmp/sf079-evidence-dry-run
python -m unittest discover -s tests -p 'test_sf079_evidence.py' -v
```

The output directory uses a SHA-256 content digest for identity. This is **tamper-evident when verified**, not physically immutable storage: local users may edit or remove files. Verification uses explicit runtime errors even under `python -O`. `evidence.json` has canonical sorted JSON keys; `manifest.json` records its digest; existing different/incomplete content is refused. Keep evidence **outside Git**. The dry run uses synthetic fixtures only, including deliberate placeholder secrets that must be redacted. This is a hash of the **sanitized stored document**, never a hash of an unavailable original HTTP response.

## Source-use checkpoint (mandatory before real acquisitions)

**Current status: UNVERIFIED / NOT AUTHORIZED BY THIS DOCUMENT.**

Before any future request to NSE:

1. Identify applicable NSE/charting website terms, market data licences and permitted personal research/automated access/storage use, with URLs or dated retained copies and responsible reviewer.
2. Determine whether retaining sanitized response bodies, OHLCV rows, chart tokens and endpoint metadata is allowed; if not, do not collect those artifacts or assume qualification is possible.
3. Specify the predeclared diagnostic instruments/windows, rate limits, allowed request methods, host environment, retry budget and stop conditions.
4. Record the decision explicitly as approved / denied / unresolved with evidence and date. Denied or unresolved must stop the live phase.
5. Capture only minimally necessary fields through a separately reviewed collection hook. This harness does **not** hook request or response objects automatically. Its caller-supplied fixtures are not independent proof of wire fields.

The offline writer uses an explicit **allowlist**, not recursive name-based redaction: request method, query-free/credential-free endpoint, approved structured parameter names and simple scalar values; response HTTP status and row count only. It **rejects** query strings, userinfo, request headers, arbitrary provider response bodies and unknown metadata. `provider_instrument_token` is a non-secret source identity, distinct from authentication credentials, and is allowed only as an alphanumeric/dot/hyphen/underscore identifier; auth tokens are never retained. This prevents preserving genuine raw NSE request/response payloads in the current preparation harness. Future real evidence capture requires a separately reviewed safe field allowlist, manual review and retention permissions. No secrets or user market-data payload should be committed.

## Remaining implementation boundary

This stage does not run P1–P6, measure retention, certify source permission, inspect corporate-action terms or alter the authoritative Gate A report. It proves only local artifact formatting, redaction of named sensitive keys, deterministic hashing, tamper detection and fail-closed nonapproved capture calls. P0 is anchored to the fork's script location, regardless of caller working directory, and reports the full Git HEAD plus tracked worktree dirty status. P0 currently prints this environment record to stdout rather than persisting it; the dry-run file contains synthetic data only. P0's printed SHA alone does not authenticate dependencies or prove a clean release build. A new feature branch must not be misrepresented as the prior qualified fork commit.

SF-079 `TIMESTAMP_SEMANTICS` stays PENDING, nsemine remains BLOCKED, Gate A NOT PASSED and Phase B NOT STARTED.

The synthetic dry-run invokes the schema gate with a literal local-only `approved` test fixture: this is **not** approval for NSE acquisition. Real source-use permissions remain UNVERIFIED. The test-only writer does not make HTTP requests.
