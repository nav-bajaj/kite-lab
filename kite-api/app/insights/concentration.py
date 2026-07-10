"""Nifty 50 concentration / attribution engine.

For any given date D, decomposes Nifty 50's move into per-constituent
contributions using the cap-weighted index methodology:

    contribution_i = weight_i * return_i
    share_of_move_i = contribution_i / index_return

Surfaces:
  - Top-3 / top-5 cumulative contribution share
  - Reliance (RIL) specific share — the single most-watched concentration risk
  - Cap-weighted (NIFTY 50 official) vs equal-weighted (mean of constituent
    returns) spread — large positive spread = narrow tape driven by big names;
    large negative spread = broad participation lifting equal weights more

Weights come from dated NSE factsheet snapshots under
`data/static/index_weights/NIFTY_50/<YYYY-MM-DD>.csv`. The loader picks
the most recent dated file. Refresh = drop a new factsheet CSV in the
folder; the loader auto-discovers it.

Constituent prices come from `nse500_data_merged/<SYMBOL>_day.csv`.
Names that aren't in our panel (e.g., very recent IPOs) are silently
dropped from attribution with `n_constituents_covered` reflecting the
coverage.

Caching: `@lru_cache` on the loaders; per-date attribution is cheap so no
disk pickle.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

from app.config import get_settings
from app.insights._paths import indices_dir


def _data_root() -> Path:
    return get_settings().data_dir


def _weights_dir() -> Path:
    return _data_root() / "data" / "static" / "index_weights" / "NIFTY_50"


def _latest_weights_file() -> Path:
    """Most recent `<YYYY-MM-DD>.csv` factsheet snapshot in the weights dir."""
    candidates = sorted(_weights_dir().glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].csv"))
    if not candidates:
        raise FileNotFoundError(
            f"No factsheet snapshot CSVs found in {_weights_dir()}. "
            "Expected files named YYYY-MM-DD.csv (e.g., 2026-04-30.csv) — "
            "see data/static/index_weights/README.md."
        )
    return candidates[-1]


def _prices_dir() -> Path:
    return _data_root() / "nse500_data_merged"


def _index_file() -> Path:
    return indices_dir() / "NIFTY_50.csv"


@lru_cache(maxsize=1)
def load_weights() -> pd.Series:
    """Symbol → weight (normalised to sum to exactly 100).

    Reads the most recent dated factsheet snapshot under
    `data/static/index_weights/NIFTY_50/`. Source weights from the NSE
    factsheet sum to ~100 with rounding; we re-normalise so attribution
    math is exactly invariant.
    """
    df = pd.read_csv(_latest_weights_file())
    df["symbol"] = df["symbol"].astype(str).str.strip()
    raw = pd.Series(df["weight_pct"].astype(float).values, index=df["symbol"].values)
    return raw * (100.0 / raw.sum())


@lru_cache(maxsize=1)
def load_constituent_closes() -> pd.DataFrame:
    """Wide DataFrame of close prices, columns=symbol (only Nifty 50 names)."""
    weights = load_weights()
    series = []
    for sym in weights.index:
        p = _prices_dir() / f"{sym}_day.csv"
        if not p.exists():
            # Some symbols use slightly different filenames (e.g., M&M).
            # Skip — attribution will be a partial denominator.
            continue
        df = pd.read_csv(p, parse_dates=["date"])[["date", "close"]]
        df = df.rename(columns={"close": sym}).set_index("date")
        series.append(df[sym])
    return pd.concat(series, axis=1).sort_index()


@lru_cache(maxsize=1)
def load_nifty50_index() -> pd.DataFrame:
    df = pd.read_csv(_index_file(), parse_dates=["date"])
    return df.set_index("date").sort_index()


@dataclass
class ConstituentContribution:
    symbol: str
    weight: float
    return_pct: float
    contribution_bps: float  # weight * return, in basis points (decimal pp * 100)
    share_of_move: Optional[float]  # contribution / index_return, fraction


@dataclass
class ConcentrationReading:
    date: pd.Timestamp
    nifty_return_pct: float
    equal_weighted_return_pct: float
    cap_vs_equal_spread_pp: float
    top_3_share_of_move: Optional[float]  # 0-1; None if index_return is ~0
    top_5_share_of_move: Optional[float]
    reliance_share_of_move: Optional[float]
    top_3_symbols: list[str]
    top_5_symbols: list[str]
    n_constituents_covered: int
    n_constituents_total: int
    constituents: list[ConstituentContribution] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


def compute_concentration(date: pd.Timestamp | None = None) -> ConcentrationReading:
    """Decompose Nifty 50's move on `date` into per-constituent contributions.

    `date` defaults to the latest available index close.
    """
    index = load_nifty50_index()
    if date is None:
        date = index.index[-1]
    else:
        date = pd.Timestamp(date)

    if date not in index.index:
        idx_loc = index.index.searchsorted(date)
        if idx_loc >= len(index.index):
            idx_loc = len(index.index) - 1
        date = index.index[idx_loc]

    idx_close_today = float(index.loc[date, "close"])
    prev_idx_pos = index.index.get_loc(date) - 1
    idx_close_prev = float(index.iloc[prev_idx_pos]["close"])
    nifty_ret_pct = (idx_close_today / idx_close_prev - 1.0) * 100.0

    weights = load_weights()
    closes = load_constituent_closes()

    cons_today = closes.loc[date] if date in closes.index else closes.iloc[
        closes.index.searchsorted(date)
    ]
    prev_pos = closes.index.searchsorted(date) - 1
    if prev_pos < 0:
        raise ValueError(f"No prior trading day in constituent panel before {date}")
    cons_prev = closes.iloc[prev_pos]

    contribs: list[ConstituentContribution] = []
    valid_returns: list[float] = []

    for sym, w in weights.items():
        if sym not in closes.columns:
            continue
        c_today = cons_today.get(sym)
        c_prev = cons_prev.get(sym)
        if pd.isna(c_today) or pd.isna(c_prev) or c_prev == 0:
            continue
        ret_pct = (float(c_today) / float(c_prev) - 1.0) * 100.0
        contrib_bps = (w / 100.0) * ret_pct * 100.0  # (weight as fraction) * pp_return * 100 → bps
        share = (contrib_bps / 100.0) / nifty_ret_pct if abs(nifty_ret_pct) > 1e-6 else None
        contribs.append(
            ConstituentContribution(
                symbol=sym,
                weight=float(w),
                return_pct=ret_pct,
                contribution_bps=contrib_bps,
                share_of_move=share,
            )
        )
        valid_returns.append(ret_pct)

    contribs.sort(key=lambda c: abs(c.contribution_bps), reverse=True)
    top3 = contribs[:3]
    top5 = contribs[:5]

    def _aggregate_share(items: list[ConstituentContribution]) -> Optional[float]:
        if abs(nifty_ret_pct) < 1e-6:
            return None
        return sum(c.contribution_bps for c in items) / 100.0 / nifty_ret_pct

    eq_weighted = sum(valid_returns) / len(valid_returns) if valid_returns else 0.0
    ril = next((c for c in contribs if c.symbol == "RELIANCE"), None)

    return ConcentrationReading(
        date=date,
        nifty_return_pct=nifty_ret_pct,
        equal_weighted_return_pct=eq_weighted,
        cap_vs_equal_spread_pp=nifty_ret_pct - eq_weighted,
        top_3_share_of_move=_aggregate_share(top3),
        top_5_share_of_move=_aggregate_share(top5),
        reliance_share_of_move=ril.share_of_move if ril else None,
        top_3_symbols=[c.symbol for c in top3],
        top_5_symbols=[c.symbol for c in top5],
        n_constituents_covered=len(contribs),
        n_constituents_total=len(weights),
        constituents=contribs,
    )
