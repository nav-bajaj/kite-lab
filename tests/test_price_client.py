import unittest
from unittest import mock
import pandas as pd
import sys
import types

# Provide a minimal kiteconnect module for import-time resolution
sys.modules.setdefault("kiteconnect", types.SimpleNamespace(KiteConnect=object))

from data_pipeline.price_client import PriceClient


class TestPriceClient(unittest.TestCase):
    def test_fetch_history_chunks_and_dedupes(self):
        kite = mock.Mock()
        kite.historical_data.side_effect = [
            [{"date": "2023-01-01 09:00:00", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100}],
            [{"date": "2023-01-02 09:00:00", "open": 2, "high": 3, "low": 2, "close": 3, "volume": 200}],
        ]

        with mock.patch("data_pipeline.price_client.find_instrument") as mock_find:
            mock_find.return_value = {"instrument_token": 123, "exchange": "NSE"}
            client = PriceClient(kite)
            df = client.fetch_history("ABC", "2023-01-01", "2023-01-03", interval="day", chunk_days=1)

        self.assertEqual(len(df), 2)
        self.assertTrue((df["date"].dt.date == pd.to_datetime(["2023-01-01", "2023-01-02"]).date).all())
        self.assertEqual(kite.historical_data.call_count, 2)
