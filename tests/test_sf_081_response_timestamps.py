"""SF-081 deterministic, network-free response timestamp regression tests."""
import unittest
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pandas as pd

from nsemine import historical
from nsemine.utilities.utils import process_historical_chart_response


def clock_ms(hour, minute, second=59):
    return int(datetime(2026, 10, 12, hour, minute, second, tzinfo=UTC).timestamp() * 1000)


def rows(times):
    return pd.DataFrame(
        [dict(time=t, open=100, high=102, low=99, close=101, volume=10)
         for t in times],
        columns=["time", "open", "high", "low", "close", "volume"],
    )


class IntradayResponseTimestampTests(unittest.TestCase):
    def decode(self, times, interval):
        return process_historical_chart_response(
            rows(times), interval,
            datetime(2026, 10, 12, 9, 15),
            datetime(2026, 10, 12, 10, 15),
        )

    def test_one_minute_variable_seconds_map_to_correct_openings(self):
        result = self.decode([
            clock_ms(9, 15, 59), clock_ms(9, 16, 53),
            clock_ms(9, 17, 55),
        ], 1)
        self.assertEqual(list(result.datetime.dt.strftime("%H:%M")), [
            "09:15", "09:16", "09:17",
        ])

    def test_five_minute_variable_seconds_map_to_correct_openings(self):
        result = self.decode([
            clock_ms(9, 19, 59), clock_ms(9, 24, 53),
            clock_ms(9, 29, 55),
        ], 5)
        self.assertEqual(list(result.datetime.dt.strftime("%H:%M")), [
            "09:15", "09:20", "09:25",
        ])

    def test_duplicate_label_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.decode([clock_ms(9, 15, 53), clock_ms(9, 15, 59)], 1)

    def test_out_of_order_rejected(self):
        with self.assertRaisesRegex(ValueError, "unordered"):
            self.decode([clock_ms(9, 16), clock_ms(9, 15)], 1)

    def test_five_minute_wrong_final_minute_rejected(self):
        with self.assertRaisesRegex(ValueError, "final candle minute"):
            self.decode([clock_ms(9, 18)], 5)

    def test_non_integral_second_rejected(self):
        with self.assertRaisesRegex(ValueError, "precision"):
            self.decode([clock_ms(9, 15) + 500], 1)

    def test_null_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.decode([clock_ms(9, 15), None], 1)

    def test_empty_response_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.decode([], 1)

    def test_unordered_provider_response_fails_closed(self):
        response = Mock()
        response.json.return_value = {"data": rows([
            clock_ms(9, 16), clock_ms(9, 15),
        ]).to_dict("records")}
        with patch.object(historical.scraper, "get_request", return_value=response):
            result = historical.__dict__["__fetch_historical_data"](
                symbol="RELIANCE", token="token",
                start_datetime=datetime(2026, 10, 12, 9, 15),
                end_datetime=datetime(2026, 10, 12, 10, 15),
                interval=1, symbol_type="Equity", raw=False,
            )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
