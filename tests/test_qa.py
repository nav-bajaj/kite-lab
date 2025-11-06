import unittest
from pathlib import Path
import pandas as pd

from data_pipeline.qa import validate_prices


class TestQA(unittest.TestCase):
    def setUp(self):
        self.path = Path("tests/temp_prices.csv")
        self.path.unlink(missing_ok=True)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_missing_file(self):
        result = validate_prices(self.path)
        self.assertTrue(result["errors"])

    def test_detects_non_positive_close(self):
        df = pd.DataFrame({"date": pd.to_datetime(["2023-01-01"]), "close": [0]})
        df.to_csv(self.path, index=False)
        result = validate_prices(self.path)
        self.assertIn("non-positive close values detected", result["errors"])

    def test_detects_gaps(self):
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01", "2023-01-10"]),
                "close": [100, 101],
            }
        )
        df.to_csv(self.path, index=False)
        result = validate_prices(self.path)
        self.assertTrue(result["warnings"])
