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
from app.insights._freshness import dir_signature, file_signature
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


# Universe-scoped concentration (founder request 2026-08-14): cap side is
# the universe's own index series (our custom nifty250 uses the official
# NIFTY LARGEMID250 analog — same construction, see
# tasks/insights_dashboard_v2/DECISIONS.md); equal side is the mean return
# of the committed universe snapshot. The weights-based per-name
# attribution (compute_concentration) stays nifty50-only — factsheet
# weights exist only for the Nifty 50.
CONCENTRATION_UNIVERSES = {
    "nifty50": ("NIFTY_50.csv", None),
    "nifty100": ("NIFTY_100.csv", "nifty100_universe.csv"),
    "nifty250": ("NIFTY_LARGEMID250.csv", "nifty250_universe.csv"),
    "nse500": ("NIFTY_500.csv", "nse500_universe.csv"),
}


def _check_universe(universe: str) -> None:
    if universe not in CONCENTRATION_UNIVERSES:
        raise ValueError(
            f"Unknown universe {universe!r}; expected one of "
            f"{tuple(CONCENTRATION_UNIVERSES)}"
        )


def _index_file(universe: str = "nifty50") -> Path:
    _check_universe(universe)
    return indices_dir() / CONCENTRATION_UNIVERSES[universe][0]


def _universe_symbols(universe: str) -> list[str]:
    """Constituents: the weights factsheet for nifty50 (its authoritative
    membership), the committed universe CSV otherwise."""
    _check_universe(universe)
    csv_name = CONCENTRATION_UNIVERSES[universe][1]
    if csv_name is None:
        return list(load_weights().index)
    df = pd.read_csv(_data_root() / "data" / "static" / csv_name)
    return df["Symbol"].astype(str).tolist()


def _weights_signature() -> tuple:
    """Cache key for the factsheet weights — the weights dir mtime, which
    bumps when a new dated factsheet CSV is dropped in (the documented
    refresh path)."""
    return (dir_signature(_weights_dir()),)


def load_weights() -> pd.Series:
    """Symbol → weight (normalised to sum to exactly 100).

    Reads the most recent dated factsheet snapshot under
    `data/static/index_weights/NIFTY_50/`. Source weights from the NSE
    factsheet sum to ~100 with rounding; we re-normalise so attribution
    math is exactly invariant.
    """
    return _load_weights_cached(_weights_signature())


@lru_cache(maxsize=2)
def _load_weights_cached(signature) -> pd.Series:
    df = pd.read_csv(_latest_weights_file())
    df["symbol"] = df["symbol"].astype(str).str.strip()
    raw = pd.Series(df["weight_pct"].astype(float).values, index=df["symbol"].values)
    return raw * (100.0 / raw.sum())


load_weights.cache_clear = _load_weights_cached.cache_clear


def load_constituent_closes(universe: str = "nifty50") -> pd.DataFrame:
    """Wide DataFrame of close prices, columns=symbol, for the universe's
    constituents."""
    return _load_constituent_closes_cached(
        universe,
        _weights_signature()
        + (dir_signature(_prices_dir(), sentinel="RELIANCE_day.csv"),),
    )


@lru_cache(maxsize=8)
def _load_constituent_closes_cached(universe, signature) -> pd.DataFrame:
    series = []
    for sym in _universe_symbols(universe):
        p = _prices_dir() / f"{sym}_day.csv"
        if not p.exists():
            # Some symbols use slightly different filenames (e.g., M&M).
            # Skip — attribution will be a partial denominator.
            continue
        df = pd.read_csv(p, parse_dates=["date"])[["date", "close"]]
        df = df.rename(columns={"close": sym}).set_index("date")
        series.append(df[sym])
    return pd.concat(series, axis=1).sort_index()


load_constituent_closes.cache_clear = _load_constituent_closes_cached.cache_clear


def load_index_series(universe: str = "nifty50") -> pd.DataFrame:
    return _load_index_series_cached(universe, file_signature(_index_file(universe)))


@lru_cache(maxsize=8)
def _load_index_series_cached(universe, signature) -> pd.DataFrame:
    df = pd.read_csv(_index_file(universe), parse_dates=["date"])
    return df.set_index("date").sort_index()


def load_nifty50_index() -> pd.DataFrame:
    """Back-compat alias — the point-in-time attribution is nifty50-only."""
    return load_index_series("nifty50")


load_index_series.cache_clear = _load_index_series_cached.cache_clear
load_nifty50_index.cache_clear = _load_index_series_cached.cache_clear


def clear_cache() -> None:
    """Drop all three concentration loaders. Wired into
    reading.clear_all_caches()."""
    _load_weights_cached.cache_clear()
    _load_constituent_closes_cached.cache_clear()
    _load_index_series_cached.cache_clear()


def compute_concentration_panel(universe: str = "nifty50") -> pd.DataFrame:
    """Daily cap-weighted vs equal-weighted return spread history for
    `universe` (nifty50 default; nifty100 / nifty250 / nse500 supported).

    Powers the dashboard's concentration chart (a positive spread means
    the heavyweights outran the average constituent — a narrow tape).
    Cap side is the ACTUAL index return; equal side is the mean of the
    current constituents' returns — with the documented caveat that the
    constituent set is today's snapshot applied backward.

    Columns: cap_ret_pct, eq_ret_pct, cap_vs_equal_spread_pp,
    spread_20d_avg_pp (NaN for the first 19 rows).
    """
    _check_universe(universe)
    index = load_index_series(universe)
    closes = load_constituent_closes(universe)
    cap = (index["close"].pct_change(fill_method=None) * 100.0).iloc[1:]
    eq = (closes.pct_change(fill_method=None) * 100.0).iloc[1:].mean(axis=1)
    panel = pd.DataFrame({"cap_ret_pct": cap, "eq_ret_pct": eq}).dropna(
        subset=["cap_ret_pct", "eq_ret_pct"]
    )
    panel["cap_vs_equal_spread_pp"] = panel["cap_ret_pct"] - panel["eq_ret_pct"]
    panel["spread_20d_avg_pp"] = panel["cap_vs_equal_spread_pp"].rolling(20).mean()
    return panel


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
