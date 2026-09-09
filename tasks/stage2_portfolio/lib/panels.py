"""Calendar-safe OHLCV panel builder for the S2 study.

Survivorship-free by construction: symbols come from the reconstructed
NSE 500 membership (tasks/index_reconstruction), prices from the merged
current-member panel plus the two ex-member backfill dirs.

Guards against the two known panel traps:
  - phantom timestamped rows (NMDC has 719 stamped 09:15:00) -> dates are
    normalized and de-duplicated before pivoting
  - ffill past a symbol's real life -> every series is masked outside
    [first real bar, last real bar] so a delisted name goes NaN rather
    than holding a flat price forever
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]

PRICE_DIRS = [
    ROOT / "nse500_data_merged",
    ROOT / "nse500_data_backfill",
    ROOT / "nse500_data_backfill_gdf",
]

MEMBERSHIP_RECON = (ROOT / "tasks/index_reconstruction/data"
                    / "nse500_membership_reconstructed.csv")
MEMBERSHIP_PROD = ROOT / "data/static/nse500_membership.csv"


def _read_one(path: Path) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    if df.empty or "close" not in df.columns or "date" not in df.columns:
        return None
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").drop_duplicates("date", keep="last")
    for c in ("open", "high", "low", "close", "volume"):
        if c not in df.columns:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["close"] > 0]
    if df.empty:
        return None
    return df.set_index("date")[["open", "high", "low", "close", "volume"]]


def locate_symbols(symbols: set[str]) -> dict[str, Path]:
    """First price dir that has each symbol wins (merged > kite > gdf)."""
    found: dict[str, Path] = {}
    for d in PRICE_DIRS:
        if not d.exists():
            continue
        for p in d.glob("*_day.csv"):
            sym = p.stem[:-4]
            if sym in symbols and sym not in found:
                found[sym] = p
    return found


def build_panels(symbols: set[str], *, calendar_source: Path | None = None) -> dict:
    """Return dict of Date x Symbol panels on one shared calendar."""
    located = locate_symbols(symbols)
    frames = {}
    for sym, path in sorted(located.items()):
        df = _read_one(path)
        if df is not None and len(df) >= 260:
            frames[sym] = df

    src = calendar_source or PRICE_DIRS[0]
    cal_dates: set[pd.Timestamp] = set()
    for p in src.glob("*_day.csv"):
        sym = p.stem[:-4]
        if sym in frames:
            cal_dates |= set(frames[sym].index)
    if not cal_dates:
        for df in frames.values():
            cal_dates |= set(df.index)
    calendar = pd.DatetimeIndex(sorted(cal_dates))

    out = {}
    for field in ("open", "high", "low", "close", "volume"):
        wide = pd.DataFrame(
            {sym: df[field].reindex(calendar) for sym, df in frames.items()},
            index=calendar,
        )
        out[field] = wide

    # Life mask from the raw (pre-ffill) close, then ffill only inside life.
    raw_close = out["close"]
    first_ok = raw_close.notna().cumsum() > 0
    last_ok = raw_close.notna()[::-1].cumsum()[::-1] > 0
    alive = first_ok & last_ok

    for field in ("open", "high", "low", "close"):
        out[field] = out[field].ffill().where(alive)
    # Volume is a flow, not a level: never carry it forward.
    out["volume"] = out["volume"].where(alive)

    ohlc_sum = out["open"] + out["high"] + out["low"] + out["close"]
    trade = ohlc_sum / 4.0
    out["trade"] = trade.where(trade > 0).fillna(out["close"])
    out["calendar"] = calendar
    out["alive"] = alive
    out["n_symbols"] = len(frames)
    out["missing"] = sorted(symbols - set(frames))
    return out


def load_membership_symbols(path: Path = MEMBERSHIP_RECON) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["effective_from"] = pd.to_datetime(df["effective_from"])
    df["effective_to"] = pd.to_datetime(df["effective_to"])
    return df
