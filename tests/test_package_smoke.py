"""Offline package import smoke test for the maintained fork."""

import unittest

import nsemine
from nsemine import historical


class PackageSmokeTests(unittest.TestCase):
    """Verify the upstream package remains importable after installation."""

    def test_package_import_and_historical_api(self):
        """Import the documented public history function without any NSE request."""
        self.assertIsNotNone(nsemine)
        self.assertTrue(callable(historical.get_stock_historical_data))


if __name__ == "__main__":
    unittest.main()
