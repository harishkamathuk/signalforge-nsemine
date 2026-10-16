"""SF-083 instrument identity evidence APIs; deterministic and offline."""
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from nsemine import historical


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class InstrumentIdentityApiTests(TestCase):
    def test_search_preserves_original_provider_candidates_and_params(self):
        payload = {
            "data": [
                {
                    "symbol": "TCS-EQ",
                    "scripcode": "11536",
                    "type": "Equity",
                    "description": "TATA CONSULTANCY SERVICES LIMITED",
                },
                {
                    "symbol": "TCS-FO",
                    "scripcode": "99999",
                    "type": "Futures",
                    "description": "TCS FUTURES",
                },
            ]
        }

        with patch.object(historical.scraper, "get_request", return_value=_Response(payload)) as request:
            candidates = historical.search_stock_instruments(
                "tcs", segment="EQ", scrip_type="Equity"
            )

        self.assertEqual(
            candidates,
            [
                {
                    "symbol": "TCS-EQ",
                    "scripcode": "11536",
                    "type": "Equity",
                    "description": "TATA CONSULTANCY SERVICES LIMITED",
                }
            ],
        )
        request.assert_called_once_with(
            url=historical.urls.search_token_url,
            params={"segment": "EQ", "symbol": "TCS"},
        )


    def test_search_rejects_mixed_malformed_candidates(self):
        payload = {
            "data": [
                {
                    "symbol": "TCS-EQ",
                    "scripcode": "11536",
                    "type": "Equity",
                },
                "malformed-candidate",
            ]
        }

        with patch.object(historical.scraper, "get_request", return_value=_Response(payload)):
            with self.assertRaisesRegex(ValueError, "malformed candidate"):
                historical.search_stock_instruments("TCS", segment="EQ")

    def test_direct_historical_fetch_uses_supplied_token_without_resolution(self):
        raw_payload = {"data": [{"time": 1, "open": 1, "high": 1, "low": 1, "close": 1}]}

        with patch.object(
            historical.scraper, "get_request", return_value=_Response(raw_payload)
        ) as request:
            result = historical.get_stock_historical_data_by_instrument(
                symbol="TCS",
                token="11536",
                symbol_type="Equity",
                start_datetime=datetime(2026, 10, 9, 9, 15),
                end_datetime=datetime(2026, 10, 9, 15, 30),
                interval=1,
                raw=True,
            )

        self.assertEqual(result, raw_payload)
        self.assertEqual(request.call_count, 1)
        _, kwargs = request.call_args
        self.assertEqual(kwargs["url"], historical.urls.nse_chart_url)
        self.assertEqual(kwargs["params"]["token"], "11536")
        self.assertEqual(kwargs["params"]["symbol"], "TCS")
        self.assertEqual(kwargs["params"]["symbolType"], "Equity")

    def test_direct_historical_fetch_rejects_missing_token_before_network(self):
        with patch.object(historical.scraper, "get_request") as request:
            with self.assertRaises(ValueError):
                historical.get_stock_historical_data_by_instrument(
                    symbol="TCS",
                    token="",
                    symbol_type="Equity",
                    start_datetime=datetime(2026, 10, 9, 9, 15),
                    end_datetime=datetime(2026, 10, 9, 15, 30),
                    interval=1,
                    raw=True,
                )
        request.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
