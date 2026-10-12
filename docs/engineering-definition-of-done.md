# Engineering Definition of Done — signalforge-nsemine

This fork follows a small set of verifiable engineering controls adapted from
[SignalForge's engineering standard](https://github.com/harishkamathuk/signalforge/blob/develop/docs/engineering-definition-of-done.md).
Issue-specific acceptance criteria remain authoritative.

## Scope and compatibility
- Keep changes narrow and reviewable; prefer existing upstream APIs and patterns.
- Preserve the Python distribution and import name `nsemine`.
- Do not silently alter instrument identity, historical OHLCV meaning, timestamps, ordering or session conventions.
- Document public API changes and upstream behavioural differences.
- Retain upstream licence, attribution and commit ancestry.

## Implementation
- Use [Python documentation conventions](python-documentation-standard.md) for new or materially modified public code.
- Add focused positive and negative tests for changed behaviour.
- Mock external HTTP for deterministic unit testing; keep live connectivity checks separate.
- Bound retries, respect rate limits and fail explicitly where results are untrustworthy.
- Never disable TLS certificate verification to make connectivity tests pass.
- Do not log or commit credentials, NSE session cookies, personal configuration or large acquired datasets.

## Review and validation
- Install package on the supported development version (initially Python 3.12).
- Run applicable offline regression tests and check changed-file formatting.
- Confirm final PR CI is green and its checks cover actual tests rather than reporting empty discovery.
- For network behaviour, record versions, symbol, endpoint, bounded date range, repeated acquisitions and response classification.
- Distinguish a successful mocked response from successful **live** NSE acquisition.
- Review risks to public API compatibility, time interpretation, provider semantics and runtime security.

## Completion
The fork PR identifies its authoritative SignalForge issue, what changed, what was not changed,
validation evidence, and any remaining blocker. Keep PRs in draft if required live validation
is outstanding. Changes merge to `develop` only after applicable evidence and review are complete.
No SignalForge trading-strategy or persistence governance is inherited by this library.
