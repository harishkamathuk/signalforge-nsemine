"""SF-081 regression tests for host-independent historical request bounds."""

import os
import time
import unittest
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from nsemine import historical


@contextmanager
def process_timezone(value):
    previous = os.environ.get("TZ")
    os.environ["TZ"] = value
    if hasattr(time, "tzset"):
        time.tzset()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        if hasattr(time, "tzset"):
            time.tzset()


class HistoricalTimezoneTests(unittest.TestCase):
    def test_naive_nse_local_bounds_are_host_independent(self):
        bounds = (datetime(2026, 10, 12, 9, 15), datetime(2026, 10, 12, 10, 15))
        results = []
        for host in ("UTC", "Europe/London", "Asia/Kolkata"):
            with self.subTest(host=host), process_timezone(host):
                results.append(tuple(historical._intraday_chart_epoch(x) for x in bounds))
        self.assertEqual(results, [results[0]] * 3)
        self.assertEqual(results[0], (
            int(datetime(2026, 10, 12, 9, 15, tzinfo=UTC).timestamp()),
            int(datetime(2026, 10, 12, 10, 15, tzinfo=UTC).timestamp()),
        ))

    def test_aware_bounds_resolve_to_same_nse_wall_time(self):
        start = datetime(2026, 10, 12, 9, 15, tzinfo=ZoneInfo("Asia/Kolkata"))
        same_instant_utc = start.astimezone(UTC)
        self.assertEqual(
            historical._intraday_chart_epoch(start),
            historical._intraday_chart_epoch(same_instant_utc),
        )
        self.assertEqual(
            historical._intraday_chart_epoch(start),
            historical._intraday_chart_epoch(datetime(2026, 10, 12, 9, 15)),
        )

    def test_transmitted_intraday_bounds_identical_across_hosts(self):
        packets = []
        for host in ("UTC", "Europe/London", "Asia/Kolkata"):
            with self.subTest(host=host), process_timezone(host):
                response = Mock()
                response.json.return_value = {"data": []}
                with patch.object(historical.scraper, "get_request", return_value=response) as get:
                    raw = historical.__dict__["__fetch_historical_data"](
                        symbol="RELIANCE", token="token",
                        start_datetime=datetime(2026, 10, 12, 9, 15),
                        end_datetime=datetime(2026, 10, 12, 10, 15),
                        interval=1, symbol_type="Equity", raw=True,
                    )
                    self.assertEqual(raw, {"data": []})
                    packets.append(get.call_args.kwargs["params"])
        self.assertEqual(packets, [packets[0]] * 3)

    def test_intraday_interval_five_uses_same_bounds(self):
        start = datetime(2026, 10, 12, 9, 15)
        end = datetime(2026, 10, 12, 10, 15)
        response = Mock()
        response.json.return_value = {"data": []}
        with patch.object(historical.scraper, "get_request", return_value=response) as get:
            historical.__dict__["__fetch_historical_data"](
                symbol="RELIANCE", token="token", start_datetime=start,
                end_datetime=end, interval=5, symbol_type="Equity", raw=True,
            )
            self.assertEqual(get.call_args.kwargs["params"]["timeInterval"], 5)
            self.assertEqual(
                get.call_args.kwargs["params"]["fromDate"],
                historical._intraday_chart_epoch(start),
            )

    def test_london_dst_change_does_not_shift_nse_wall_time(self):
        for date in ((2026, 1, 12), (2026, 10, 12)):
            with self.subTest(date=date), process_timezone("Europe/London"):
                wall = datetime(*date, 9, 15)
                expected = int(datetime(*date, 9, 15, tzinfo=UTC).timestamp())
                self.assertEqual(historical._intraday_chart_epoch(wall), expected)


if __name__ == "__main__":
    unittest.main()
