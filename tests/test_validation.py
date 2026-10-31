import unittest

from forecast import get_history, forecast


class TestValidation(unittest.TestCase):
    def test_symbol_validation(self):
        with self.assertRaises(ValueError):
            get_history("UNKNOWN", "1h", 100)

    def test_interval_validation(self):
        with self.assertRaises(ValueError):
            get_history("BTCUSDT", "12h", 100)

    def test_lookback_validation(self):
        with self.assertRaises(ValueError):
            forecast("BTCUSDT", "1h", 0, 24, 1, "cpu")

    def test_samples_validation(self):
        with self.assertRaises(ValueError):
            forecast("BTCUSDT", "1h", 400, 24, 0, "cpu")


if __name__ == "__main__":
    unittest.main()
