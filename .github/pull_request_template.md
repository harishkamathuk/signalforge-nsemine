## Work item
- Authoritative issue (SignalForge, if applicable):
- Upstream reference (if applicable):
- Source branch / target: `chore/*` or `fix/*` → `develop`

## Scope and non-goals
What changed and why?

What is deliberately out of scope?

## Compatibility and data boundary
- [ ] Existing `nsemine` package/import and public API contracts are preserved, or changes are documented.
- [ ] NSE instrument identity, returned OHLCV fields and timestamp interpretation are unchanged, or differences have focused evidence.
- [ ] Transport authentication, HTTP sessions, retries and rate limiting reviewed where applicable.
- [ ] No secrets/cookies, credentials or large historical datasets committed.

State **not applicable** where no relevant boundary changed.

## Tests and evidence
- [ ] Applicable offline tests passed
- [ ] Package installs and imports with supported Python
- [ ] CI passed for the final commit
- [ ] Any relevant style/whitespace checks passed
- [ ] Live NSE results recorded separately when connectivity is part of the change

Commands, observed results, and links to CI:

## Documentation and risk
Public API/docstring or documentation updates:

Material risks, review findings, fixes and regression evidence:

## Merge readiness
Outstanding limitations, live validation still required, and follow-up:

**Do not claim mock HTTP tests prove production NSE connectivity.**
