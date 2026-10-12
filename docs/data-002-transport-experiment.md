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
