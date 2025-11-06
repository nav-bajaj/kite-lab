import unittest
from pathlib import Path

import pandas as pd


STATIC_DIR = Path("data/static")
NSE500_PATH = STATIC_DIR / "nse500_universe.csv"
INSTRUMENTS_PATH = Path("data/instruments_full.csv")


class TestStaticData(unittest.TestCase):
    def test_nse500_universe_integrity(self):
        self.assertTrue(NSE500_PATH.exists(), "Missing NSE 500 universe CSV in data/static/")
        df = pd.read_csv(NSE500_PATH)
        self.assertEqual(len(df), 500, f"Expected 500 rows, found {len(df)}")

        expected_cols = {"Company Name", "Industry", "Symbol", "Series", "ISIN Code"}
        missing = expected_cols - set(df.columns)
        self.assertFalse(missing, f"Missing columns: {missing}")
        self.assertTrue(df["Symbol"].is_unique, "Duplicate symbols detected in NSE 500 universe")
        dummy_symbols = {sym for sym in df["Symbol"] if sym.upper().startswith("DUMMY")}
        self.assertFalse(dummy_symbols, f"Placeholder symbols found: {sorted(dummy_symbols)}")

    def test_nifty100_symbol_present(self):
        self.assertTrue(INSTRUMENTS_PATH.exists(), "instruments_full.csv not found")
        df = pd.read_csv(INSTRUMENTS_PATH)
        row = df[(df["tradingsymbol"] == "NIFTY 100") & (df["exchange"] == "NSE")]
        self.assertFalse(row.empty, "NIFTY 100 benchmark symbol not found in instruments list")

        token = int(row.iloc[0]["instrument_token"])
        self.assertEqual(token, 260617, f"Unexpected instrument token for NIFTY 100: {token}")


if __name__ == "__main__":
    unittest.main()
