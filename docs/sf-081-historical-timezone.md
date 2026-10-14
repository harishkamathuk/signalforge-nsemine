# SF-081 — Historical intraday request timezone correctness

Tracker: https://github.com/harishkamathuk/signalforge/issues/203

## Established defect

The prior intraday request encoder used `int(datetime.timestamp()) + 19800`.
For naive datetime inputs, `timestamp()` uses the host process timezone;
therefore identical NSE trading-session wall-clock bounds transmitted different
values under `Europe/London`, `UTC`, and `Asia/Kolkata`.

This defect is separate from DATA-002's HTTP transport selection.

## Focused correction

For **intraday** requests, the encoder now explicitly treats naive datetimes
as NSE local wall-clock values and converts aware datetimes to
`Asia/Kolkata` before generating the existing chart-provider *wall-clock-encoded*
epoch-seconds representation. No process timezone or DST setting affects the
encoded values.

The output uses the previously observed chart request convention:
`2026-10-12 09:15 IST` is encoded as Unix-shaped seconds for
`2026-10-12 09:15 UTC` — **not** the true UTC epoch for the instant.
This is a description of the historically used wire mapping, **not yet an
independently proven NSE API contract**.

Daily/weekly/monthly request encoding and all response timestamp processing
are intentionally unchanged to avoid conflating separate semantics.

## Verification and remaining gate

Offline regression tests cover identical 1m request payloads across three
process timezones, aware datetime equivalence, 5m request bounds, and a
London DST/non-DST comparison. The tests do **not** make NSE network calls.

Before treating this as SF-081 fully resolved or promoting SF-079 timestamp
semantics to PROVEN, execute a bounded, sanitized live NSE probe on the
updated fork revision and check:

- request bounds/endpoint plus original raw response `time` values;
- the meaning of response epochs, observed intra-minute offsets, and interval
  open/close labelling before any rounding or subtraction;
- expected first/last canonical 1m and 5m bar identities;
- identical canonical timestamps and OHLCV across process timezones;
- immutable probe artifact/content hashes, observation timestamp, and exact
  installed revision identity.

The existing `utils.process_historical_chart_response` manipulates raw
timestamps by applying an interval-dependent offset, filtering by local-looking
clock time, and rounding; those transformations **must be validated separately**
before claiming canonical timestamp correctness.

Do not change SignalForge's ADR-010 historical-bar contract to accommodate
the provider, nor treat this fix as a Gate A SELECT decision.
