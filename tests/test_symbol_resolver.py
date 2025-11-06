import unittest
from unittest import mock
import pandas as pd
from pathlib import Path

from data_pipeline import symbol_resolver


class TestSymbolResolver(unittest.TestCase):
    def setUp(self):
        self.temp_path = Path("tests/temp_instruments.csv")
        df = pd.DataFrame(
            [
                {"tradingsymbol": "ABC", "instrument_token": 1, "exchange": "NSE", "name": "ABC LTD"},
                {"tradingsymbol": "ABC", "instrument_token": 2, "exchange": "BSE", "name": "ABC LTD"},
            ]
        )
        df.to_csv(self.temp_path, index=False)
        symbol_resolver._load_instruments.cache_clear()

    def tearDown(self):
        self.temp_path.unlink(missing_ok=True)
        symbol_resolver._load_instruments.cache_clear()

    def test_find_instrument_prefers_nse(self):
        info = symbol_resolver.find_instrument("ABC", path=self.temp_path)
        self.assertEqual(info["instrument_token"], 1)
        self.assertEqual(info["exchange"], "NSE")

    def test_find_instrument_falls_back(self):
        info = symbol_resolver.find_instrument("ABC", exchange_priority=["BSE"], path=self.temp_path)
        self.assertEqual(info["instrument_token"], 2)
        self.assertEqual(info["exchange"], "BSE")

    def test_missing_symbol_raises(self):
        with self.assertRaises(symbol_resolver.InstrumentNotFoundError):
            symbol_resolver.find_instrument("XYZ", path=self.temp_path)
