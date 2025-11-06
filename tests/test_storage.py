import unittest
from pathlib import Path
import pandas as pd

from data_pipeline.storage import save_dataframe, load_dataframe


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.path = Path("tests/temp_store.csv")
        self.path.unlink(missing_ok=True)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_save_and_load(self):
        df = pd.DataFrame({"date": pd.to_datetime(["2023-01-01"]), "close": [100]})
        save_dataframe(df, self.path)
        loaded = load_dataframe(self.path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded.iloc[0]["close"], 100)

    def test_load_missing_returns_empty(self):
        missing_path = Path("tests/missing.csv")
        missing_path.unlink(missing_ok=True)
        loaded = load_dataframe(missing_path)
        self.assertTrue(loaded.empty)
