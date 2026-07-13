"""Sector subgroup tracker — within-sector splits that the headline
sector indices hide.

Default sector indices (NIFTY BANK, NIFTY AUTO, NIFTY PHARMA, etc.) blend
heterogeneous constituents into one cap-weighted number. But "Banks +1%"
can mean very different things depending on whether private banks led
(HDFCBANK / ICICIBANK / KOTAKBANK / AXISBANK / INDUSINDBK) or PSU banks
led (SBIN / PNB / CANBK / BANKBARODA / UNIONBANK).

This module tracks the splits explicitly. For each subgroup we compute:

  - rs_5d / rs_20d / rs_60d (vs Nifty 50): mean of constituent returns
    minus Nifty's return over the same window
  - pct_above_200dma: share of subgroup constituents above their 200-DMA
  - today_chg_pct: equal-weighted mean of constituent daily returns today
  - rs_60d_prev_week: rs_60d as of 5 trading days ago (for WoW delta)
  - n_covered / n_total: coverage in our price panel

Membership is hand-curated below — there's no NSE source-of-truth for
"private vs PSU banks" or "OEMs vs ancillaries"; the groupings reflect
how Indian market commentary actually talks about these splits. Update
manually if a corporate action changes who fits where.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.config import get_settings
from app.insights._freshness import dir_signature, file_signature
from app.insights._paths import indices_dir


# ─────────── membership ───────────
#
# Every member symbol below has been verified to exist in
# nse500_data_merged/. Members missing from the panel are silently
# dropped at compute time (n_covered tracks that).

SUBGROUPS: dict[str, dict] = {
    "private_banks": {
        "label": "Private banks",
        "parent_sector": "NIFTY_BANK",
        "members": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "INDUSINDBK"],
    },
    "psu_banks": {
        "label": "PSU banks",
        "parent_sector": "NIFTY_BANK",
        "members": ["SBIN", "PNB", "BANKBARODA", "CANBK", "UNIONBANK"],
    },
    "large_pharma": {
        "label": "Large-cap pharma",
        "parent_sector": "NIFTY_PHARMA",
        "members": ["SUNPHARMA", "DRREDDY", "CIPLA"],
    },
    "mid_pharma": {
        "label": "Mid-cap pharma",
        "parent_sector": "NIFTY_PHARMA",
        "members": ["LUPIN", "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE"],
    },
    "auto_oems": {
        "label": "Auto OEMs (passenger + 2W)",
        "parent_sector": "NIFTY_AUTO",
        "members": ["MARUTI", "TMPV", "M&M", "EICHERMOT",
                    "BAJAJ-AUTO", "HEROMOTOCO", "TVSMOTOR"],
    },
    "auto_ancillaries": {
        "label": "Auto ancillaries",
        "parent_sector": "NIFTY_AUTO",
        "members": ["MOTHERSON", "BHARATFORG", "BOSCHLTD", "EXIDEIND"],
    },
    "oil_marketing": {
        "label": "Oil marketing companies",
        "parent_sector": "NIFTY_ENERGY",
        "members": ["BPCL", "IOC", "HINDPETRO"],
    },
    "private_power": {
        "label": "Private power",
        "parent_sector": "NIFTY_ENERGY",
        "members": ["TATAPOWER", "ADANIPOWER", "ADANIGREEN", "ADANIENSOL"],
    },
    "psu_power": {
        "label": "PSU power",
        "parent_sector": "NIFTY_ENERGY",
        "members": ["NTPC", "POWERGRID", "COALINDIA"],
    },
    "it_large": {
        "label": "Large-cap IT",
        "parent_sector": "NIFTY_IT",
        "members": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
    },
    "it_mid": {
        "label": "Mid-cap IT",
        "parent_sector": "NIFTY_IT",
        "members": ["PERSISTENT", "COFORGE", "MPHASIS", "OFSS"],
    },
}

# Sibling pairs — used for "spread" commentary. Order matters only for
# the sign convention (positive spread = first one leading).
SIBLING_PAIRS: list[tuple[str, str]] = [
    ("private_banks", "psu_banks"),
    ("large_pharma", "mid_pharma"),
    ("auto_oems", "auto_ancillaries"),
    ("it_large", "it_mid"),
    ("private_power", "psu_power"),
]


# ─────────── data shape ───────────

@dataclass
class SubgroupSnapshot:
    subgroup: str
    label: str
    parent_sector: str
    n_total: int
    n_covered: int
    today_chg_pct: Optional[float]      # equal-weighted mean daily return
    rs_5d: Optional[float]              # mean constituent return - Nifty, over 5d
    rs_20d: Optional[float]
    rs_60d: Optional[float]
    rs_60d_prev_week: Optional[float]   # rs_60d 5 sessions ago, for WoW delta
    rs_60d_wow_delta: Optional[float]   # rs_60d - rs_60d_prev_week
    pct_above_200dma: Optional[float]   # 0..1
    members_covered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SubgroupSpread:
    pair: tuple[str, str]
    spread_60d_pp: Optional[float]      # rs_60d[a] - rs_60d[b], in pp
    label: str                          # e.g. "Private banks vs PSU banks"

    def to_dict(self) -> dict:
        return {"pair": list(self.pair),
                "spread_60d_pp": self.spread_60d_pp,
                "label": self.label}


# ─────────── data loading ───────────

def _data_root() -> Path:
    return get_settings().data_dir


def _prices_dir() -> Path:
    return _data_root() / "nse500_data_merged"


def _nifty_file() -> Path:
    return indices_dir() / "NIFTY_50.csv"


@lru_cache(maxsize=1)
def _all_members() -> tuple[str, ...]:
    seen: list[str] = []
    for g in SUBGROUPS.values():
        for m in g["members"]:
            if m not in seen:
                seen.append(m)
    return tuple(seen)


def load_close_panel() -> pd.DataFrame:
    """Wide DataFrame of subgroup-member close prices (cols=symbol)."""
    return _load_close_panel_cached(
        dir_signature(_prices_dir(), sentinel="RELIANCE_day.csv")
    )


@lru_cache(maxsize=2)
def _load_close_panel_cached(signature) -> pd.DataFrame:
    series = []
    for sym in _all_members():
        p = _prices_dir() / f"{sym}_day.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, parse_dates=["date"])[["date", "close"]]
        df = df.rename(columns={"close": sym}).set_index("date")
        series.append(df[sym])
    return pd.concat(series, axis=1).sort_index()


load_close_panel.cache_clear = _load_close_panel_cached.cache_clear


def load_nifty_close() -> pd.Series:
    return _load_nifty_close_cached(file_signature(_nifty_file()))


@lru_cache(maxsize=2)
def _load_nifty_close_cached(signature) -> pd.Series:
    df = pd.read_csv(_nifty_file(), parse_dates=["date"]).set_index("date").sort_index()
    return df["close"]


load_nifty_close.cache_clear = _load_nifty_close_cached.cache_clear


def clear_cache() -> None:
    _load_close_panel_cached.cache_clear()
    _load_nifty_close_cached.cache_clear()


# ─────────── computation ───────────

def _rs_over(panel: pd.DataFrame, nifty: pd.Series,
             asof: pd.Timestamp, lookback: int,
             members: list[str]) -> Optional[float]:
    """Mean constituent return minus Nifty return, all over `lookback`
    trading days ending at `asof`. Returns None if data insufficient."""
    if asof not in panel.index or asof not in nifty.index:
        return None
    end_idx = panel.index.get_loc(asof)
    if end_idx < lookback:
        return None
    start_close = panel.iloc[end_idx - lookback]
    end_close = panel.iloc[end_idx]
    cons_ret = (end_close[members] / start_close[members]) - 1.0
    cons_mean = float(cons_ret.dropna().mean())

    n_end_idx = nifty.index.get_loc(asof)
    if n_end_idx < lookback:
        return None
    nifty_ret = float(nifty.iloc[n_end_idx] / nifty.iloc[n_end_idx - lookback] - 1.0)

    return cons_mean - nifty_ret


def _compute_one(name: str, group: dict, panel: pd.DataFrame,
                 nifty: pd.Series, asof: pd.Timestamp) -> SubgroupSnapshot:
    members_total = group["members"]
    members_covered = [m for m in members_total if m in panel.columns]

    today_chg: Optional[float] = None
    pct_200: Optional[float] = None
    if members_covered and asof in panel.index:
        idx = panel.index.get_loc(asof)
        if idx >= 1:
            today = panel.iloc[idx][members_covered]
            prev = panel.iloc[idx - 1][members_covered]
            chg = (today / prev) - 1.0
            today_chg = float(chg.dropna().mean()) if chg.dropna().size else None

        if idx >= 200:
            sma_200 = panel.iloc[idx - 200:idx][members_covered].mean()
            close = panel.iloc[idx][members_covered]
            above = (close > sma_200) & close.notna() & sma_200.notna()
            n_valid = int((close.notna() & sma_200.notna()).sum())
            pct_200 = float(above.sum() / n_valid) if n_valid else None

    rs_5 = _rs_over(panel, nifty, asof, 5, members_covered) if members_covered else None
    rs_20 = _rs_over(panel, nifty, asof, 20, members_covered) if members_covered else None
    rs_60 = _rs_over(panel, nifty, asof, 60, members_covered) if members_covered else None

    # WoW delta = rs_60 today minus rs_60 5 sessions ago
    rs_60_prev: Optional[float] = None
    wow_delta: Optional[float] = None
    if members_covered:
        if asof in panel.index:
            idx = panel.index.get_loc(asof)
            if idx >= 5:
                prev_asof = panel.index[idx - 5]
                rs_60_prev = _rs_over(panel, nifty, prev_asof, 60, members_covered)
                if rs_60 is not None and rs_60_prev is not None:
                    wow_delta = rs_60 - rs_60_prev

    return SubgroupSnapshot(
        subgroup=name,
        label=group["label"],
        parent_sector=group["parent_sector"],
        n_total=len(members_total),
        n_covered=len(members_covered),
        today_chg_pct=today_chg,
        rs_5d=rs_5,
        rs_20d=rs_20,
        rs_60d=rs_60,
        rs_60d_prev_week=rs_60_prev,
        rs_60d_wow_delta=wow_delta,
        pct_above_200dma=pct_200,
        members_covered=members_covered,
    )


def get_subgroup_snapshot(asof: pd.Timestamp | None = None
                          ) -> dict[str, SubgroupSnapshot]:
    """Per-subgroup snapshot for `asof` (defaults to latest)."""
    panel = load_close_panel()
    nifty = load_nifty_close()
    if asof is None:
        asof = panel.index.max()
    asof = pd.Timestamp(asof)
    if asof not in panel.index:
        valid = panel.index[panel.index <= asof]
        if valid.empty:
            return {}
        asof = valid.max()
    return {name: _compute_one(name, g, panel, nifty, asof)
            for name, g in SUBGROUPS.items()}


def get_sibling_spreads(asof: pd.Timestamp | None = None
                        ) -> list[SubgroupSpread]:
    """Pair-level 60d RS spread (group_a - group_b) for each sibling pair."""
    snaps = get_subgroup_snapshot(asof)
    out: list[SubgroupSpread] = []
    for a, b in SIBLING_PAIRS:
        sa, sb = snaps.get(a), snaps.get(b)
        if not sa or not sb:
            continue
        if sa.rs_60d is None or sb.rs_60d is None:
            spread = None
        else:
            spread = (sa.rs_60d - sb.rs_60d) * 100.0  # to percentage points
        out.append(SubgroupSpread(
            pair=(a, b),
            spread_60d_pp=spread,
            label=f"{sa.label} vs {sb.label}",
        ))
    return out
