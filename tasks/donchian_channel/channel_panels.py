"""Donchian channel panels for the donchian_channel research task.

Builds Date x Symbol high/low/close panels from raw `<SYM>_day.csv` files
(the shared `load_price_panels()` drops high/low, so we read raw CSVs) and
computes Donchian bands.

Causality convention: all bands are the PRIOR N-day extreme (rolling window
shifted 1 day). Two reasons:
  - the engine exit `close < don_low` can never fire against a window that
    includes the same day's low;
  - a breakout "cross above the N-day high" is only detectable against the
    prior window (an inclusive window makes close/upper <= 1 by identity
    whenever the day's high >= close).
`nearness_to_high` offers inclusive=True for the George-Hwang ratio, which
is still causal (uses data through the signal date only).

Run as a script for the Phase 1 sanity gates:
    python tasks/donchian_channel/channel_panels.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PRICES_DIR = ROOT / "nse500_data_merged"
UNIVERSE_CSV = ROOT / "data/static/nse500_universe.csv"


def load_universe_symbols(universe_csv: Path = UNIVERSE_CSV) -> list[str]:
    df = pd.read_csv(universe_csv)
    return sorted(df["Symbol"].dropna().astype(str).unique())


def load_ohlc_panels(prices_dir: Path = DEFAULT_PRICES_DIR,
                     symbols: list[str] | None = None) -> dict:
    """Return dict of Date x Symbol panels: high, low, close, trade (OHLC/4).

    Mirrors data_pipeline.loaders.load_price_panels (sorted index, ffill) so
    the calendar is identical to what the engine sees.
    """
    want = set(symbols) if symbols is not None else None
    rows = []
    for csv_path in sorted(Path(prices_dir).glob("*_day.csv")):
        symbol = csv_path.stem.replace("_day", "")
        if want is not None and symbol not in want:
            continue
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty or not {"high", "low", "close"}.issubset(df.columns):
            continue
        df["symbol"] = symbol
        df["trade_price"] = df[["open", "high", "low", "close"]].mean(axis=1) \
            if "open" in df.columns else df["close"]
        rows.append(df[["date", "symbol", "high", "low", "close", "trade_price"]])
    if not rows:
        raise RuntimeError(f"No usable price files in {prices_dir}")
    combined = pd.concat(rows, ignore_index=True)
    panels = {}
    for col, name in (("high", "high"), ("low", "low"),
                      ("close", "close"), ("trade_price", "trade")):
        p = combined.pivot(index="date", columns="symbol", values=col).sort_index()
        panels[name] = p.ffill()
    return panels


def donchian_upper(high: pd.DataFrame, n: int) -> pd.DataFrame:
    """Prior N-day high: rolling max over [t-n, t-1]."""
    return high.rolling(n, min_periods=n).max().shift(1)


def donchian_lower(low: pd.DataFrame, n: int) -> pd.DataFrame:
    """Prior N-day low: rolling min over [t-n, t-1]."""
    return low.rolling(n, min_periods=n).min().shift(1)


def channel_position(close: pd.DataFrame, upper: pd.DataFrame,
                     lower: pd.DataFrame) -> pd.DataFrame:
    """Where close sits in the prior channel, 0..1 (can exceed on breakout).

    Identical in form to stochastic %K / (100 - Williams %R) — documented so
    we don't double-count it as a novel feature.
    """
    width = upper - lower
    return (close - lower) / width.where(width > 0)


def nearness_to_high(close: pd.DataFrame, high: pd.DataFrame,
                     n: int = 252, inclusive: bool = True) -> pd.DataFrame:
    """George-Hwang ratio: close / N-day high.

    inclusive=True (default) is the published definition (window includes
    the signal date; ratio <= 1). inclusive=False uses the prior window so
    fresh breakouts read > 1.
    """
    roll = high.rolling(n, min_periods=n).max()
    if not inclusive:
        roll = roll.shift(1)
    return close / roll


def breakout_cross(close: pd.DataFrame, upper_prior: pd.DataFrame) -> pd.DataFrame:
    """True where close crosses above the prior N-day high today and did not
    already sit above it yesterday (fresh breakout, not continuation)."""
    above = close > upper_prior
    return above & ~above.shift(1, fill_value=False)


def _sanity() -> int:
    print("[phase1] loading panels (full universe, merged deep history)")
    symbols = load_universe_symbols()
    panels = load_ohlc_panels(symbols=symbols)
    high, low, close = panels["high"], panels["low"], panels["close"]
    print(f"  panel shape {close.shape}, {close.index.min().date()} .. "
          f"{close.index.max().date()}")

    failures = 0

    # Gate 1: manual band check on RELIANCE at an arbitrary fixed date.
    raw = pd.read_csv(DEFAULT_PRICES_DIR / "RELIANCE_day.csv",
                      parse_dates=["date"]).set_index("date").sort_index()
    t = pd.Timestamp("2020-06-15")
    idx = raw.index.get_loc(t)
    manual_upper = raw["high"].iloc[idx - 55:idx].max()
    panel_upper = donchian_upper(high, 55).loc[t, "RELIANCE"]
    ok = np.isclose(manual_upper, panel_upper)
    print(f"  gate1 RELIANCE 55d prior high @ {t.date()}: manual={manual_upper:.2f} "
          f"panel={panel_upper:.2f} -> {'OK' if ok else 'FAIL'}")
    failures += 0 if ok else 1

    # Gate 2: no-lookahead — recompute bands on data truncated at T; values at
    # T must be identical to the full-history computation.
    t = pd.Timestamp("2022-03-04")
    for fn, src, name in ((donchian_upper, high, "upper55"),
                          (donchian_lower, low, "lower20")):
        n = 55 if name == "upper55" else 20
        full = fn(src, n).loc[t]
        trunc = fn(src.loc[:t], n).loc[t]
        same = full.dropna().round(6).equals(trunc.dropna().round(6)) and \
            full.isna().equals(trunc.isna())
        print(f"  gate2 causality {name} @ {t.date()}: "
              f"{'OK' if same else 'FAIL'}")
        failures += 0 if same else 1

    # Gate 3: exit-rule feasibility — close < prior-20d-low must actually
    # occur (it can't with an unshifted window).
    don_low20 = donchian_lower(low, 20)
    hits = (close < don_low20).sum().sum()
    print(f"  gate3 prior-20d-low breaches present: {int(hits)} "
          f"({'OK' if hits > 0 else 'FAIL'})")
    failures += 0 if hits > 0 else 1
    unshifted = low.rolling(20, min_periods=20).min()
    bad = (close < unshifted).sum().sum()
    print(f"  gate3b inclusive-window breaches (expect 0): {int(bad)} "
          f"({'OK' if bad == 0 else 'FAIL'})")
    failures += 0 if bad == 0 else 1

    # Gate 4: coverage by year (symbols with valid 252d nearness).
    near = nearness_to_high(close, high, 252)
    cov = near.notna().sum(axis=1).resample("YE").last()
    print("  gate4 symbols with valid 252d nearness at each year-end:")
    for d, v in cov.items():
        print(f"    {d.year}: {int(v)}")

    print(f"[phase1] {'ALL GATES PASSED' if failures == 0 else f'{failures} FAILURES'}")
    return failures


if __name__ == "__main__":
    raise SystemExit(_sanity())
