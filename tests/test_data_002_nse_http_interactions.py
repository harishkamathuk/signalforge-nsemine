"""Network-free NSE HTTP interaction tests using real scraper/historical entrypoints.

These are protocol fixtures, not evidence of live NSE connectivity.
"""
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from nsemine.bin import scraper
from nsemine import historical
from nsemine.utilities import urls


def response(status=200, data=None, content_type="application/json", body=""):
    item = MagicMock()
    item.status_code = status
    item.headers = {"content-type": content_type}
    item.text = body
    item.json.return_value = data
    if status >= 400:
        item.raise_for_status.side_effect = RuntimeError("HTTP failure")
    return item


class NSEHTTPInteractionTests(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.session.cookies.get_dict.return_value = {"mock-session": "fixture-only"}
        self.sessions = patch.object(scraper, "_get_sync_session", return_value=self.session)
        self.sessions.start()
        self.addCleanup(self.sessions.stop)
        self.sleep = patch.object(scraper.time, "sleep")
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def test_bootstrap_cookies_from_nse_page(self):
        with patch.object(scraper.auth, "set_session_token") as saved:
            self.session.get.return_value = response()
            self.assertEqual(scraper._refresh_session_token(force=True), {"mock-session": "fixture-only"})
            saved.assert_called_once_with({"mock-session": "fixture-only"})
            self.assertEqual(self.session.get.call_args.kwargs["url"], urls.first_boy)

    def test_bootstrap_tls_failure_returns_no_cookies(self):
        self.session.get.side_effect = RuntimeError("curl: (35) SSL_connect failed")
        with patch.object(scraper.auth, "set_session_token") as saved:
            self.assertIsNone(scraper._refresh_session_token(force=True))
            saved.assert_not_called()

    def _request(self, replies):
        self.session.get.side_effect = replies
        with patch.object(scraper.auth, "get_session_token", return_value={"mock-session": "fixture-only"}), \
             patch.object(scraper.auth, "set_session_token"):
            return scraper.get_request(urls.search_token_url, params={"symbol": "BAJAJ-AUTO"})

    def test_symbol_request_success(self):
        result = response(data={"data": [{"symbol": "BAJAJ-AUTO-EQ", "scripcode": 16669, "type": "Equity", "description": "BAJAJ AUTO"}]})
        self.assertIs(self._request([result]), result)
        self.assertEqual(self.session.get.call_args.kwargs["params"]["symbol"], "BAJAJ-AUTO")

    def test_tls_failure_then_success(self):
        result = response(data={"data": []})
        with patch.object(scraper, "_refresh_session_token", return_value={"mock-session": "fixture-only"}):
            self.assertIs(self._request([RuntimeError("curl: (35) SSL_connect failed"), result]), result)
        self.assertEqual(self.session.get.call_count, 2)

    def test_tls_failure_exhausts_retries(self):
        with patch.object(scraper, "_refresh_session_token", return_value={"mock-session": "fixture-only"}):
            self.assertIsNone(self._request([RuntimeError("curl: (35) SSL_connect failed")] * scraper.MAX_RETRIES))
        self.assertEqual(self.session.get.call_count, scraper.MAX_RETRIES)

    def test_403_refresh_then_success(self):
        blocked = response(status=403)
        succeeded = response(data={"data": []})
        with patch.object(scraper, "_refresh_session_token", return_value={"mock-session": "fixture-only"}):
            self.assertIs(self._request([blocked, succeeded]), succeeded)
        blocked.close.assert_called_once()

    def test_429_retries_and_closes_response(self):
        limited = response(status=429)
        limited.headers["Retry-After"] = "0"
        succeeded = response(data={"data": []})
        self.assertIs(self._request([limited, succeeded]), succeeded)
        limited.close.assert_called_once()

    def test_html_block_causes_recovery(self):
        blocked = response(content_type="text/html", body="<html>Access Denied</html>")
        succeeded = response(data={"data": []})
        with patch.object(scraper, "_refresh_session_token", return_value={"mock-session": "fixture-only"}):
            self.assertIs(self._request([blocked, succeeded]), succeeded)
        blocked.close.assert_called_once()

    def test_nonretryable_http_error_fails(self):
        bad = response(status=400)
        self.assertIsNone(self._request([bad]))
        self.assertEqual(self.session.get.call_count, 1)
        bad.close.assert_called_once()

    def test_symbol_lookup_uses_mock_nse_response(self):
        payload = {"data": [{"symbol": "BAJAJ-AUTO-EQ", "scripcode": 16669, "type": "Equity", "description": "BAJAJ AUTO"}]}
        with patch.object(historical.scraper, "get_request", return_value=response(data=payload)) as fetch:
            result = getattr(historical, "__get_script_token")("BAJAJ-AUTO")
        self.assertEqual(result, ("BAJAJ-AUTO", 16669, "Equity"))
        self.assertEqual(fetch.call_args.kwargs["url"], urls.search_token_url)

    def test_symbol_lookup_unavailable_returns_none(self):
        with patch.object(historical.scraper, "get_request", return_value=None):
            self.assertIsNone(getattr(historical, "__get_script_token")("BAJAJ-AUTO"))

    def test_historical_1m_and_5m_request_params(self):
        sample = {"status": "ok", "data": [{"time": 1750000000000, "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10}]}
        for interval in (1, 5):
            with self.subTest(interval=interval), \
                 patch.object(historical.scraper, "get_request", return_value=response(data=sample)) as fetch:
                # Avoid symbol lookup bypass: exercise public entrypoint with mocked NSE API.
                symbol = {"data": [{"symbol": "BAJAJ-AUTO-EQ", "scripcode": 16669, "type": "Equity", "description": "BAJAJ AUTO"}]}
                fetch.side_effect = [response(data=symbol), response(data=sample)]
                result = historical.get_stock_historical_data(
                    "BAJAJ-AUTO", datetime(2025, 6, 16, 9, 15),
                    datetime(2025, 6, 16, 9, 20), interval=interval, raw=True,
                )
                self.assertEqual(result, sample)
                self.assertEqual(fetch.call_args.kwargs["url"], urls.nse_chart_url)
                self.assertEqual(fetch.call_args.kwargs["params"]["timeInterval"], interval)
                self.assertEqual(fetch.call_args.kwargs["params"]["token"], 16669)

    def test_malformed_historical_json_returns_none(self):
        symbols = response(data={"data": [{"symbol": "BAJAJ-AUTO-EQ", "scripcode": 16669, "type": "Equity", "description": "BAJAJ AUTO"}]})
        malformed = response()
        malformed.json.side_effect = ValueError("Invalid JSON")
        with patch.object(historical.scraper, "get_request", side_effect=[symbols, malformed]):
            self.assertIsNone(historical.get_stock_historical_data(
                "BAJAJ-AUTO", datetime(2025, 6, 16), datetime(2025, 6, 17), interval=1, raw=True))


if __name__ == "__main__":
    unittest.main()
