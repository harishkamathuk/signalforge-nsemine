# SF-081 — Validated NSE historical response clock mapping

Tracker: https://github.com/harishkamathuk/signalforge/issues/203

## Scope and observed evidence

On 2026-10-14, bounded RELIANCE acquisitions for 2026-10-12
09:15–10:15 NSE-local were captured from fork commit
`db3984db5db121faddd43b6d574aa6c9cd8be66b`, using the
`requests` transport. Three host process timezones (UTC,
Europe/London, Asia/Kolkata) yielded identical 1m and 5m raw and
processed SHA-256 fingerprints. There were 60 one-minute and 12
five-minute candles, with no missing opening buckets. A separate
local evidence acquisition recorded all raw and processed OHLCV rows;
five-minute OHLCV equalled five-minute aggregation of one-minute
candles in all 12 buckets.

Those are observations for one instrument and one hour, **not**
an authoritative NSE specification, nor an SF-079 Gate A SELECT.

## Response timestamp interpretation used for validated 1m and 5m

- The NSE chart response `time` is an integer millisecond count
  formatted like a Unix timestamp but observed to represent the
  **NSE-local wall clock**, not a verified UTC instant.
- The provider value occurs within the **final minute** of its
  candle. It is not necessarily `:59` seconds (observed `:53`–`:59`).
- A 1m raw clock at 09:15:53–59 labels the 09:15 opening.
  A 5m raw clock at 09:19:53–59 labels the 09:15 opening.
  Opening labels are *naive NSE-local* in this fork's legacy API.
  SignalForge's future adapter must explicitly attach Asia/Kolkata
  and convert to its canonical timestamp representation; do not
  mistake the raw `time` milliseconds for a true UTC instant.
- Regular-session labels must be 09:15 <= open < 15:30.
  5m buckets are anchored at 09:15 and align on five-minute boundaries.
- For these two intervals, processing rejects missing/non-integer
  millisecond timestamps, unexpected subsecond precision,
  duplicate or unordered raw timestamps, duplicate opening labels,
  and timestamps outside the candle's final minute. It also rejects
  candles outside the explicitly requested date/time bounds: opening
  at or after the requested start, entire interval completed by the
  exclusive requested end. The legacy chart wire bounds are decoded
  as NSE wall-clock-shaped seconds; aware caller bounds are interpreted
  in Asia/Kolkata. Partial end buckets are not accepted. A failure
  propagates from the timestamp decoder; the legacy public
  historical fetch wrapper returns `None` and does not yield
  a corrupted DataFrame.
- For these validated 1m/5m regular-session calls, all response rows
  are validated **before any filtering**. Unexpected pre/post-market
  records cause explicit failure rather than silently disappearing.
  Other intervals retain legacy filtering. The API's outer historical
  wrapper still returns None after reporting a processing failure.
- Basic OHLCV plausibility is checked (finite positive prices, nonnegative
  volume, high/low contain open/close). This is not independent source
  verification or a replacement for SF-079 missing/correction policies.
- Timestamps merely inside the final minute are accepted, including :00.
  This is **bucket alignment only**: it does not prove a candle is completed.
  Completed-candle admission must be independently enforced downstream.
- Missing intervals are **not** synthesized or rejected here, nor are arbitrary
  historical windows required to contain every minute. The
  SignalForge adapter/source qualification owns missing-bar policy.

Daily/weekly/monthly and other intraday intervals are **not**
covered by these validations. Their conversion behaviour remains
unchanged; do not generalize this contract to them.

## Reproduction and limitations

Offline tests synthesize observed raw timestamp patterns and corrupt
cases without redistributing provider market data:

`python -m unittest discover -s tests -p 'test_sf_081_*.py' -v`

The source identity/token was not independently snapshotted, and
full provider response metadata was not retained by the probe.
The raw provider clock convention is empirically supported but
not vendor-documented. SF-079 Gate A remains **BLOCKED**;
retention, corporate actions, source-use terms and repeatability
must be qualified separately. No trading strategy or execution
semantics change is authorized by this fork patch.
