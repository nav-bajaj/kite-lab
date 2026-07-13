"""Relative-strength ranking engine (C2 of insights_v2).

Ranks the NSE 500 by a composite momentum score and exposes the machinery
the screener + momentum-inflection stories need: cross-sectional rank
(1 = strongest), percentile, sector-relative rank, and a 21-trading-day
rank delta that surfaces the "biggest improvers" cohort.

## Composite methodology (documented per C2.1)

The firm's production momentum portfolios (see `scripts/om25_v3.py`,
`scripts/tl25_v3.py`, `scripts/build_momentum_signals_flexible.py`) share
one shape: compute a raw momentum metric per stock, then **percentile-rank
it cross-sectionally across the eligible universe** and blend. We reuse
that shape here so the screener's notion of "strength" is consistent with
how the firm already defines momentum.

The RS composite blends the cross-sectional percentile ranks of the
trailing 1 / 3 / 6 / 12-month total returns:

    composite = 0.10·pct(1m) + 0.20·pct(3m) + 0.30·pct(6m) + 0.40·pct(12m)

Longer horizons carry more weight — the 6-to-12-month formation window is
where the cross-sectional momentum effect is best documented
(Jegadeesh & Titman 1993 and India-specific replications), while the
1-month term is kept small because short-horizon returns carry a reversal
component. These weights are a transparent design choice, quoted verbatim
in the Learn explainer; they are not fitted to maximise any backtest.

A stock needs full 12-month history to receive a composite (and therefore
a rank); recent listings are left unranked rather than ranked on partial
data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from app.insights import sector_constituents as _sc
from app.insights import stock_metrics as _sm

# Composite blend weights (sum to 1.0) — see module docstring.
RS_WEIGHTS: dict[str, float] = {"1m": 0.10, "3m": 0.20, "6m": 0.30, "12m": 0.40}

_HORIZON_TD = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}
RANK_DELTA_WINDOW = 21       # trading days for the momentum-inflection delta


@dataclass
class RSEntry:
    symbol: str
    rs_score: float | None       # blended percentile composite, 0..1
    rank: int | None             # 1 = strongest across the ranked universe
    percentile: float | None     # 0..100, higher = stronger
    sector_rank: int | None
    sector_size: int | None
    rank_21d_ago: int | None
    rank_delta_21d: int | None   # positive = improved (moved toward rank 1)

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────── core computation ───────────────────────────

def compute_composite_panel(close: pd.DataFrame) -> pd.DataFrame:
    """Return a (date × symbol) panel of composite RS scores in [0, 1].

    Each horizon return is percentile-ranked cross-sectionally per date,
    then blended by RS_WEIGHTS. NaN where any horizon lacks history.
    """
    composite = None
    for h, w in RS_WEIGHTS.items():
        ret = close.pct_change(_HORIZON_TD[h], fill_method=None)
        pct = ret.rank(axis=1, pct=True)
        term = w * pct
        composite = term if composite is None else composite + term
    return composite


def _ranks_for_row(composite_row: pd.Series) -> pd.Series:
    """Dense-min ordinal rank, 1 = highest composite. NaN stays NaN."""
    return composite_row.rank(method="min", ascending=False)


def compute_rs_table(
    asof: pd.Timestamp,
    close: pd.DataFrame,
    sectors_map: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, RSEntry]:
    """Full RS table as of `asof`. Pure over the injected close panel."""
    asof = pd.Timestamp(asof)
    sub = close.loc[:asof]
    if sub.empty:
        return {}

    composite = compute_composite_panel(sub)
    row = composite.iloc[-1]
    ranks = _ranks_for_row(row)
    pctile = row.rank(pct=True) * 100.0

    # 21-day-ago ranks for the delta / inflection cohort
    prev_ranks = None
    if len(composite) > RANK_DELTA_WINDOW:
        prev_ranks = _ranks_for_row(composite.iloc[-1 - RANK_DELTA_WINDOW])

    # Sector-relative ranks: rank the composite within each sector.
    sector_rank: dict[str, int] = {}
    sector_size: dict[str, int] = {}
    if sectors_map:
        by_sector: dict[str, list[str]] = {}
        for sym in row.index:
            if pd.isna(row.get(sym)):
                continue
            for sec in sectors_map.get(sym, ()):  # a stock may span sectors
                by_sector.setdefault(sec, []).append(sym)
        # Rank within each sector by composite (highest = 1). A stock in
        # multiple sectors keeps its best (numerically lowest) sector rank.
        for sec, syms in by_sector.items():
            ordered = sorted(syms, key=lambda s: row[s], reverse=True)
            for i, sym in enumerate(ordered, start=1):
                if sym not in sector_rank or i < sector_rank[sym]:
                    sector_rank[sym] = i
                    sector_size[sym] = len(syms)

    out: dict[str, RSEntry] = {}
    for sym in row.index:
        score = row.get(sym)
        has = pd.notna(score)
        r = ranks.get(sym)
        pa = prev_ranks.get(sym) if prev_ranks is not None else np.nan
        rank_now = int(r) if pd.notna(r) else None
        rank_prev = int(pa) if pd.notna(pa) else None
        delta = (rank_prev - rank_now) if (rank_now is not None
                                           and rank_prev is not None) else None
        out[str(sym)] = RSEntry(
            symbol=str(sym),
            rs_score=float(score) if has else None,
            rank=rank_now,
            percentile=float(pctile.get(sym)) if has else None,
            sector_rank=sector_rank.get(sym),
            sector_size=sector_size.get(sym),
            rank_21d_ago=rank_prev,
            rank_delta_21d=delta,
        )
    return out


def get_inflection_cohort(
    asof: pd.Timestamp,
    close: pd.DataFrame,
    top_n: int = 25,
) -> list[RSEntry]:
    """The biggest 21-day rank improvers (momentum inflection). Observation
    only — any forward-return framing requires a passing validity study
    (see tasks/insights_v2/VALIDITY/inflection.md)."""
    table = compute_rs_table(asof, close)
    improvers = [e for e in table.values()
                 if e.rank_delta_21d is not None and e.rank_delta_21d > 0]
    improvers.sort(key=lambda e: e.rank_delta_21d, reverse=True)
    return improvers[:top_n]


# ─────────────────────────── loaders + caching ───────────────────────────

def _load_close() -> pd.DataFrame:
    panels = _sm.load_ohlcv_panels()
    return panels["close"] if panels else pd.DataFrame()


def _symbol_sectors() -> dict[str, tuple[str, ...]]:
    try:
        from app.insights.sector_constituents import get_symbol_to_sectors
        return get_symbol_to_sectors()
    except Exception:
        return {}


_MEM_CACHE: dict[str, dict[str, RSEntry]] = {}


def _source_key(date_key: str) -> str:
    """Per-date cache key folded with the underlying data signature (price
    panel + sector snapshot) so a same-date data update reloads."""
    sig = _sm._panel_signature() + _sc._signature()
    return f"{date_key}|{_sm._sig_token(sig)}"


def get_rs_table(asof: pd.Timestamp | None = None) -> dict[str, RSEntry]:
    """RS table over the live NSE 500 panel, cached per as-of date."""
    close = _load_close()
    if close.empty:
        return {}
    valid = close.index[close.index <= pd.Timestamp(asof)] if asof is not None \
        else close.index
    if not len(valid):
        return {}
    resolved = valid.max()
    key = _source_key(resolved.date().isoformat())
    if key in _MEM_CACHE:
        return _MEM_CACHE[key]
    table = compute_rs_table(resolved, close, sectors_map=_symbol_sectors())
    _MEM_CACHE[key] = table
    return table


def get_live_inflection_cohort(
    asof: pd.Timestamp | None = None,
    top_n: int = 25,
) -> list[RSEntry]:
    close = _load_close()
    if close.empty:
        return []
    valid = close.index[close.index <= pd.Timestamp(asof)] if asof is not None \
        else close.index
    if not len(valid):
        return []
    return get_inflection_cohort(valid.max(), close, top_n=top_n)


def clear_cache() -> None:
    _MEM_CACHE.clear()
