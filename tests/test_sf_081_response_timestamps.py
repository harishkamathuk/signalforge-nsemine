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

    def test_wrong_date_rejected(self):
        next_day = clock_ms(9, 15) + 86_400_000
        with self.assertRaisesRegex(ValueError, "requested date/time"):
            self.decode([next_day], 1)

    def test_previous_date_rejected(self):
        prior = clock_ms(9, 15) - 86_400_000
        with self.assertRaisesRegex(ValueError, "requested date/time"):
            self.decode([prior], 1)

    def test_before_requested_start_rejected(self):
        with self.assertRaisesRegex(ValueError, "requested date/time"):
            process_historical_chart_response(
                rows([clock_ms(9, 19), clock_ms(9, 20)]), 1,
                datetime(2026, 10, 12, 9, 20),
                datetime(2026, 10, 12, 10, 15),
            )

    def test_at_or_after_requested_end_rejected(self):
        with self.assertRaisesRegex(ValueError, "requested date/time"):
            self.decode([clock_ms(10, 15)], 1)

    def test_five_minute_partial_end_bucket_rejected(self):
        frame = rows([clock_ms(10, 14)])
        with self.assertRaisesRegex(ValueError, "requested date/time"):
            process_historical_chart_response(
                frame, 5, datetime(2026, 10, 12, 9, 15),
                datetime(2026, 10, 12, 10, 12),
            )

    def test_five_minute_end_boundary_accepted(self):
        result = self.decode([clock_ms(10, 14, 55)], 5)
        self.assertEqual(str(result.datetime.iloc[0]), "2026-10-12 10:10:00")

    def test_encoded_wire_request_bounds_supported(self):
        frame = rows([clock_ms(9, 19)])
        result = process_historical_chart_response(
            frame, 5,
            int(datetime(2026, 10, 12, 9, 15, tzinfo=UTC).timestamp()),
            int(datetime(2026, 10, 12, 10, 15, tzinfo=UTC).timestamp()),
        )
        self.assertEqual(str(result.datetime.iloc[0]), "2026-10-12 09:15:00")

    def test_outside_session_not_silently_filtered(self):
        with self.assertRaisesRegex(ValueError, "out-of-session"):
            self.decode([clock_ms(9, 15), clock_ms(16, 0)], 1)

    def test_pre_market_not_silently_filtered(self):
        with self.assertRaisesRegex(ValueError, "out-of-session"):
            self.decode([clock_ms(8, 0), clock_ms(9, 15)], 1)

    def test_one_minute_zero_seconds_is_bucket_member_only(self):
        # :00 passes shape validation but is not proof of a completed candle.
        result = self.decode([clock_ms(9, 15, 0)], 1)
        self.assertEqual(str(result.datetime.iloc[0]), "2026-10-12 09:15:00")

    def test_gap_is_not_synthesized(self):
        result = self.decode([clock_ms(9, 15), clock_ms(9, 17)], 1)
        self.assertEqual(len(result), 2)

    def test_invalid_ohlc_rejected(self):
        frame = rows([clock_ms(9, 15)])
        frame.loc[0, 'high'] = 98
        with self.assertRaisesRegex(ValueError, "Inconsistent"):
            process_historical_chart_response(
                frame, 1, datetime(2026, 10, 12, 9, 15),
                datetime(2026, 10, 12, 10, 15),
            )

    def test_invalid_volume_rejected(self):
        frame = rows([clock_ms(9, 15)])
        frame.loc[0, 'volume'] = -1
        with self.assertRaisesRegex(ValueError, "Invalid intraday"):
            process_historical_chart_response(
                frame, 1, datetime(2026, 10, 12, 9, 15),
                datetime(2026, 10, 12, 10, 15),
            )

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
