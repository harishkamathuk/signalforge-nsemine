# SF-079 Stage 2 — offline qualification evidence preparation

This folder's tool `tools/sf079_evidence.py` is **offline only**. It does not import the nsemine historical requester or initiate network access, and does not implement a SignalForge provider adapter. It supports P0 environment reporting and a synthetic sanitized evidence/manifest dry run. **It cannot certify live-source evidence or grant use permissions.**

Run from the fork checkout:

```bash
python tools/sf079_evidence.py p0
python tools/sf079_evidence.py dry-run --out /tmp/sf079-evidence-dry-run
python -m unittest discover -s tests -p 'test_sf079_evidence.py' -v
```

The output directory uses a SHA-256 content digest for identity. `evidence.json` has canonical sorted JSON keys; `manifest.json` records its digest; existing different/incomplete content is refused. Keep evidence **outside Git**. The dry run uses synthetic fixtures only, including deliberate placeholder secrets that must be redacted. This is a hash of the **sanitized stored document**, never a hash of an unavailable original HTTP response.

## Source-use checkpoint (mandatory before real acquisitions)

**Current status: UNVERIFIED / NOT AUTHORIZED BY THIS DOCUMENT.**

Before any future request to NSE:

1. Identify applicable NSE/charting website terms, market data licences and permitted personal research/automated access/storage use, with URLs or dated retained copies and responsible reviewer.
2. Determine whether retaining sanitized response bodies, OHLCV rows, chart tokens and endpoint metadata is allowed; if not, do not collect those artifacts or assume qualification is possible.
3. Specify the predeclared diagnostic instruments/windows, rate limits, allowed request methods, host environment, retry budget and stop conditions.
4. Record the decision explicitly as approved / denied / unresolved with evidence and date. Denied or unresolved must stop the live phase.
5. Capture only minimally necessary fields through a separately reviewed collection hook. This harness does **not** hook request or response objects automatically. Its caller-supplied fixtures are not independent proof of wire fields.

The recursive redactor is a defense-in-depth filter based on sensitive key names; it is **not an assurance** that free-text values, URL query strings or provider-returned unlabelled fields contain no credentials. Real capture requires strict allowlisted fields, manual review and a safe retention location. No secrets or user market-data payload should be committed.

## Remaining implementation boundary

This stage does not run P1–P6, measure retention, certify source permission, inspect corporate-action terms or alter the authoritative Gate A report. It proves only local artifact formatting, redaction of named sensitive keys, deterministic hashing, tamper detection and fail-closed nonapproved capture calls. Fork implementation identity for P0 is read directly from the local Git checkout; a new feature branch must not be misrepresented as the prior qualified fork commit.

SF-079 `TIMESTAMP_SEMANTICS` stays PENDING, nsemine remains BLOCKED, Gate A NOT PASSED and Phase B NOT STARTED.
