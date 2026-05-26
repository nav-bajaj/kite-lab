"""Tests for sector-constituent snapshots fetched by
`scripts/fetch_sector_constituents.py`.

Validates against the most-recent snapshot directory under
`data/static/sector_constituents/`. No network access required — the
fetch script is responsible for putting data on disk; these tests
verify that the data is well-formed and usable downstream.

Test categories:
  1. Snapshot existence  — at least one snapshot dir exists
  2. Per-sector schema   — every CSV has the expected columns
  3. Per-sector counts   — within plausible NSE-published ranges
  4. Symbol hygiene      — non-empty, unique, no obvious garbage
  5. Cross-reference     — every Symbol exists in our NSE 500 panel
                            (i.e., we have price data to compute breadth)
  6. Known-stock anchors — well-known stocks live in their expected sector
"""
import unittest
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SECTOR_CONSTITUENTS_DIR = REPO_ROOT / "data" / "static" / "sector_constituents"
PRICE_PANEL_DIR = REPO_ROOT / "nse500_data_merged"

EXPECTED_COLUMNS = {"Company Name", "Industry", "Symbol", "Series", "ISIN Code"}

EXPECTED_SECTORS = {
    "NIFTY_BANK", "NIFTY_IT", "NIFTY_PHARMA", "NIFTY_FMCG", "NIFTY_AUTO",
    "NIFTY_METAL", "NIFTY_REALTY", "NIFTY_ENERGY", "NIFTY_MEDIA",
    "NIFTY_FIN_SERVICE", "NIFTY_CONSUMER_DURABLES", "NIFTY_CONSUMPTION",
}

# Sector size ranges (mirror the warning bands in fetch_sector_constituents.py
# but slightly tighter — failures here mean something went wrong in ingest).
SECTOR_SIZE_RANGE = {
    "NIFTY_BANK":              (8, 20),
    "NIFTY_IT":                (8, 20),
    "NIFTY_PHARMA":            (8, 25),
    "NIFTY_FMCG":              (8, 20),
    "NIFTY_AUTO":              (8, 20),
    "NIFTY_METAL":             (8, 20),
    "NIFTY_REALTY":            (5, 20),
    "NIFTY_ENERGY":            (8, 50),
    "NIFTY_MEDIA":             (3, 15),
    "NIFTY_FIN_SERVICE":       (15, 35),
    "NIFTY_CONSUMER_DURABLES": (8, 20),
    "NIFTY_CONSUMPTION":       (15, 40),
}

# Anchor stocks: assert these are present in their expected sector. If NSE
# rebalances and removes one, the test will fail loudly — a useful signal that
# the universe has shifted significantly.
ANCHOR_STOCKS = {
    "NIFTY_BANK":              ["HDFCBANK", "ICICIBANK", "AXISBANK", "SBIN", "KOTAKBANK"],
    "NIFTY_IT":                ["TCS", "INFY", "WIPRO", "HCLTECH"],
    "NIFTY_PHARMA":            ["SUNPHARMA", "DRREDDY", "CIPLA"],
    "NIFTY_FMCG":              ["HINDUNILVR", "ITC", "NESTLEIND"],
    # TATAMOTORS was demerged in 2024 → TMPV (passenger vehicles) is now in NIFTY AUTO
    "NIFTY_AUTO":              ["MARUTI", "TMPV", "M&M", "BAJAJ-AUTO"],
    "NIFTY_METAL":             ["TATASTEEL", "JSWSTEEL", "HINDALCO"],
    "NIFTY_REALTY":            ["DLF"],
    "NIFTY_ENERGY":            ["RELIANCE", "ONGC"],
    "NIFTY_MEDIA":             ["ZEEL"],
    "NIFTY_FIN_SERVICE":       ["HDFCBANK", "ICICIBANK", "BAJFINANCE"],
    "NIFTY_CONSUMER_DURABLES": ["TITAN", "HAVELLS"],
    "NIFTY_CONSUMPTION":       ["HINDUNILVR", "ITC", "MARUTI"],
}


def _latest_snapshot_dir() -> Path:
    """Return the path to the latest YYYY-MM snapshot directory."""
    if not SECTOR_CONSTITUENTS_DIR.exists():
        raise FileNotFoundError(
            f"No snapshots directory at {SECTOR_CONSTITUENTS_DIR}. "
            f"Run scripts/fetch_sector_constituents.py first."
        )
    candidates = sorted(p for p in SECTOR_CONSTITUENTS_DIR.iterdir() if p.is_dir())
    if not candidates:
        raise FileNotFoundError(
            f"No snapshot subdirectories under {SECTOR_CONSTITUENTS_DIR}. "
            f"Run scripts/fetch_sector_constituents.py first."
        )
    return candidates[-1]


def _load_sector(snapshot_dir: Path, sector: str) -> pd.DataFrame:
    path = snapshot_dir / f"{sector}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing sector CSV: {path}")
    return pd.read_csv(path)


def _available_price_symbols() -> set[str]:
    """Symbols for which we have price files (used for cross-reference test)."""
    if not PRICE_PANEL_DIR.exists():
        return set()
    return {p.stem.replace("_day", "") for p in PRICE_PANEL_DIR.glob("*_day.csv")}


class TestSectorConstituentsSnapshot(unittest.TestCase):
    """Snapshot-level tests — existence, completeness."""

    @classmethod
    def setUpClass(cls):
        cls.snapshot_dir = _latest_snapshot_dir()

    def test_snapshot_directory_exists(self):
        self.assertTrue(self.snapshot_dir.is_dir(),
                        f"Snapshot dir not found: {self.snapshot_dir}")

    def test_all_expected_sectors_present(self):
        files = {p.stem for p in self.snapshot_dir.glob("*.csv")}
        missing = EXPECTED_SECTORS - files
        self.assertFalse(
            missing,
            f"Snapshot {self.snapshot_dir.name} is missing sectors: {sorted(missing)}",
        )


class TestSectorConstituentsSchema(unittest.TestCase):
    """Per-sector schema and content validation."""

    @classmethod
    def setUpClass(cls):
        cls.snapshot_dir = _latest_snapshot_dir()
        cls.dfs = {s: _load_sector(cls.snapshot_dir, s) for s in EXPECTED_SECTORS}
        cls.price_symbols = _available_price_symbols()

    def test_schema_columns(self):
        for sector, df in self.dfs.items():
            with self.subTest(sector=sector):
                missing = EXPECTED_COLUMNS - set(df.columns)
                self.assertFalse(
                    missing,
                    f"{sector}: missing columns {sorted(missing)}; "
                    f"got {sorted(df.columns)}",
                )

    def test_size_range(self):
        for sector, df in self.dfs.items():
            lo, hi = SECTOR_SIZE_RANGE[sector]
            with self.subTest(sector=sector):
                self.assertGreaterEqual(
                    len(df), lo,
                    f"{sector}: {len(df)} rows < expected lower bound {lo}",
                )
                self.assertLessEqual(
                    len(df), hi,
                    f"{sector}: {len(df)} rows > expected upper bound {hi}",
                )

    def test_symbols_non_empty_and_unique(self):
        for sector, df in self.dfs.items():
            with self.subTest(sector=sector):
                symbols = df["Symbol"].astype(str).str.strip()
                empties = symbols[symbols.isin(("", "nan", "NaN", "None"))]
                self.assertTrue(empties.empty,
                                f"{sector}: empty Symbol values: {empties.tolist()}")
                self.assertTrue(symbols.is_unique,
                                f"{sector}: duplicate Symbols: "
                                f"{symbols[symbols.duplicated()].tolist()}")

    def test_company_names_non_empty(self):
        for sector, df in self.dfs.items():
            with self.subTest(sector=sector):
                names = df["Company Name"].astype(str).str.strip()
                empties = names[names.isin(("", "nan", "NaN", "None"))]
                self.assertTrue(empties.empty,
                                f"{sector}: empty Company Name values")

    def test_no_dummy_placeholders(self):
        """NSE sometimes publishes DUMMY* placeholder rows for pending
        corporate actions (e.g., Vedanta demerger). The fetch script
        filters them out; this test guards against the filter being
        accidentally weakened."""
        for sector, df in self.dfs.items():
            with self.subTest(sector=sector):
                dummies = df[df["Symbol"].str.upper().str.startswith("DUMMY")]
                self.assertTrue(
                    dummies.empty,
                    f"{sector}: DUMMY placeholder rows survived filter: "
                    f"{dummies['Symbol'].tolist()}",
                )

    def test_isin_codes_well_formed(self):
        """ISIN format: INE/IND + 9 alphanumeric (total 12 chars). Loose check."""
        import re
        isin_re = re.compile(r"^IN[A-Z0-9]{10}$")
        for sector, df in self.dfs.items():
            with self.subTest(sector=sector):
                isins = df["ISIN Code"].astype(str).str.strip()
                bad = [i for i in isins if not isin_re.match(i)]
                self.assertFalse(bad, f"{sector}: malformed ISINs: {bad[:5]}")

    def test_series_is_equity(self):
        """All entries should be in the EQ (equity) series."""
        for sector, df in self.dfs.items():
            with self.subTest(sector=sector):
                series = df["Series"].astype(str).str.strip().str.upper().unique()
                self.assertTrue(
                    set(series).issubset({"EQ", "BE"}),
                    f"{sector}: unexpected Series values {series}",
                )

    # Sectors where we accept partial price coverage. These include small-cap
    # constituents outside our NSE 500 panel; downstream breadth computations
    # should treat them as "low-confidence" sectors. Documented here so the
    # coverage gap is explicit and tracked.
    PARTIAL_COVERAGE_SECTORS = {"NIFTY_MEDIA"}

    def test_symbols_have_price_data(self):
        """At least 70% of each sector's constituents must have price data in
        our NSE 500 panel — otherwise breadth on that sector is statistically
        too thin. Exception: PARTIAL_COVERAGE_SECTORS get a 30% floor, with the
        understanding that downstream code may flag them as low-confidence."""
        if not self.price_symbols:
            self.skipTest("No price panel at nse500_data_merged/; skipping cross-ref")
        DEFAULT_MIN = 0.70
        PARTIAL_MIN = 0.30
        for sector, df in self.dfs.items():
            with self.subTest(sector=sector):
                symbols = set(df["Symbol"].astype(str).str.strip())
                covered = symbols & self.price_symbols
                missing = sorted(symbols - self.price_symbols)
                coverage = len(covered) / len(symbols) if symbols else 0
                threshold = PARTIAL_MIN if sector in self.PARTIAL_COVERAGE_SECTORS else DEFAULT_MIN
                self.assertGreaterEqual(
                    coverage, threshold,
                    f"{sector}: only {coverage*100:.0f}% coverage "
                    f"({len(covered)}/{len(symbols)}; threshold {threshold*100:.0f}%). "
                    f"Missing: {missing}",
                )

    def test_anchor_stocks_present(self):
        """Well-known stocks should still be in their expected sector. If NSE
        rebalances and removes one, this fails loudly — a useful signal."""
        for sector, expected_symbols in ANCHOR_STOCKS.items():
            df = self.dfs[sector]
            symbols = set(df["Symbol"].astype(str).str.strip())
            for expected in expected_symbols:
                with self.subTest(sector=sector, stock=expected):
                    self.assertIn(
                        expected, symbols,
                        f"{sector}: expected anchor stock {expected} not found. "
                        f"Possible NSE rebalance — verify the snapshot.",
                    )


if __name__ == "__main__":
    unittest.main()
