# DATA-002: synchronous transport compatibility experiment

Tracker: https://github.com/harishkamathuk/signalforge/issues/188

The standard nsemine synchronous HTTP transport is `curl_cffi`. In some
environments it fails with `curl (35): BoringSSL SSL_connect` before the
NSE application responds. This change offers an explicit, opt-in alternative
for **synchronous** requests only. It does not modify async requests.

## Windows PowerShell

```powershell
$env:NSEMINE_SYNC_HTTP_TRANSPORT = "requests"
python -m pip install -e .
python -m unittest discover -s tests -p "test_data_002_*.py" -v
```

Run the existing documented `historical.get_stock_historical_data` API
against a bounded NSE-equity session and compare both backends. Test NSE
bootstrap, symbol discovery, one-minute and five-minute history separately.

To return to upstream behaviour, remove the environment variable or set
it to `curl_cffi`. Unsupported values are rejected.

## Limits and verification requirements

- Both backends retain certificate verification. No TLS bypass is provided.
- A successful HTTP connection is not proof of usable historical data.
- The NSE may reject a standard `requests` fingerprint with 403/HTML or
  another application-level block. Do not treat such outcomes as success.
- No claim of improved reliability is made until actual live tests succeed.
- Record the Python/runtime, packages, exact symbol identity, time ranges,
  return values, timestamps, and repeated-acquisition results.
- The tests above are offline unit checks. They do not replace live NSE
  bootstrap, symbol and history tests.
- An async transport alternative would require separate evidence and scope.
- Never commit NSE cookies or authentication material to the repository.

## Live verification — WSL2, 14 October 2026

The owner tested this fork at commit `1ca0e733` on Python 3.12.3,
WSL2 Linux 6.6.87.2, `curl_cffi` 0.16.3, `requests` 2.34.2 and pandas 3.0.6.
Both transports bootstrapped NSE successfully and returned HTTP 200 with
20 symbol matches for RELIANCE. Under the explicitly diagnostic process setting
`TZ=Asia/Kolkata`, both returned 60 one-minute candles for the historical
09:15–10:15 IST window on 12 October 2026 (matching summary metrics).
Both returned 12 five-minute candles, with full timestamp/OHLCV DataFrame
comparison passing. Five repeated acquisitions per transport were all
successful and equivalent. See the [recorded live-test evidence](https://github.com/harishkamathuk/signalforge-nsemine/pull/1#issuecomment-6167792048).

These results demonstrate **functional compatibility for this bounded case**,
not that the alternative backend is more reliable: the original intermittent
`curl (35)` failure did not reproduce, and longer-run comparisons were not made.

**Separate data-contract defect:** The existing historical API uses naive
`datetime.timestamp()` followed by a fixed IST offset; the same intended
09:15–10:15 request retrieved a 13:45–14:44 window under `Europe/London`.
The `TZ` setting above was a diagnostic, **not a general production workaround**.
Timestamp semantics must be resolved through SignalForge's historical-data
contract independently of DATA-002. No timestamp conversion is changed here.
