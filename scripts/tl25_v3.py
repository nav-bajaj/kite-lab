"""TL25 v3 utilities — for use with `_clean_engine.run_strategy`.

V2 spec (May 2026 parameter review locked-in stack):

  Score (equal 1/3 weights):
    Persistence       — % of last 252 trading days where Close > 100 DMA
    Drawdown Control  — (Close / 126-day rolling high) ** 2  (concave squared)
    Momentum          — 63-day return, percentile-ranked among ELIGIBLE stocks

  Eligibility (trend gate — pre-filter before scoring):
    Close > 200 DMA
    50 DMA > 200 DMA
    200 DMA today > 200 DMA 20 trading days ago (slope rising)

  Sizing / cadence:
    Top-25, exit-buffer 20 (drop below rank 45)
    Bi-weekly entry (every other Friday signal → next-trading-day exec)
    Weekly exit checks (Friday signal → next-day exec)
    Equal 1/N, max 7.5% per stock, drift after entry
    20 bps slippage

  Exits (V2):
    Close < 200 DMA on weekly check
    5x 20-day ATR-equivalent trailing stop, no floor

For v3 retune we expose all of the above as parameters and let the
sweep harness pick the best combination on the 2009-2016 IS window.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


V2_LOCKED = dict(
    universe_csv="data/static/nse500_universe.csv",  # historical default
    cadence="biweekly",
    persistence_window=252,
    dma_short=50,
    dma_long=200,
    dma_persist_ref=100,
    drawdown_window=126,
    drawdown_concavity=2,  # squared
    momentum_window=63,
    w_persistence=1/3,
    w_drawdown=1/3,
    w_momentum=1/3,
    top_n=25,
    exit_buffer=20,
    max_weight=0.075,
    slippage=0.002,
    atr_mult=5.0,
    atr_min_floor=0.0,
    use_dma_exit=True,
    use_trailing_stop=True,
)


# V3 LOCKED — post 2026 OOS retune (NSE 500, A3 weights + weekly rank-exit)
V3_LOCKED = dict(
    universe_csv="data/static/nse500_universe.csv",
    cadence="biweekly",                # bi-weekly entry, weekly exit checks
    persistence_window=252,
    dma_short=50,
    dma_long=200,
    dma_persist_ref=100,
    drawdown_window=126,
    drawdown_concavity=2,
    momentum_window=63,
    # A3 weights: offensive P+M, light DD
    w_persistence=0.40,
    w_drawdown=0.20,
    w_momentum=0.40,
    top_n=25,
    exit_buffer=20,
    max_weight=0.075,
    slippage=0.002,
    # Stop: 20% fixed DD from peak (no ATR multiplier, no DMA exit)
    atr_mult=0.0,
    atr_min_floor=0.20,
    use_dma_exit=False,
    use_trailing_stop=True,
    # Rank-exit every Friday (not just biweekly) — modest DD reduction
    weekly_rank_check=True,
    # No regime tilt
    regime_panel=None,
    bear_exposure=0.0,
)


def build_tl25_panels(close_panel: pd.DataFrame, *,
                      dma_short: int = 50, dma_long: int = 200,
                      dma_persist_ref: int = 100,
                      persistence_window: int = 252,
                      drawdown_window: int = 126,
                      drawdown_concavity: float = 2.0,
                      momentum_window: int = 63,
                      slope_lookback: int = 20) -> dict:
    """Pre-compute all panels needed for TL25 scoring + eligibility.

    Returns dict with:
      - eligibility   (Date × Symbol bool)
      - persistence   (Date × Symbol float in [0, 1])
      - drawdown      (Date × Symbol float in [0, 1])
      - momentum_raw  (Date × Symbol float — N-day return)
      - sma_short, sma_long, sma_persist_ref (for downstream reuse)
    """
    sma_short = close_panel.rolling(dma_short, min_periods=dma_short).mean()
    sma_long = close_panel.rolling(dma_long, min_periods=dma_long).mean()
    sma_persist_ref_p = close_panel.rolling(dma_persist_ref,
                                             min_periods=dma_persist_ref).mean()

    # Eligibility
    cond1 = close_panel > sma_long
    cond2 = sma_short > sma_long
    cond3 = sma_long > sma_long.shift(slope_lookback)
    eligibility = cond1 & cond2 & cond3

    # Persistence: % of last N days where Close > persist-ref DMA
    above_ref = (close_panel > sma_persist_ref_p).astype(float)
    persistence = above_ref.rolling(persistence_window,
                                     min_periods=persistence_window).mean()

    # Drawdown control: (close / N-day rolling high) ^ concavity
    rolling_high = close_panel.rolling(drawdown_window,
                                        min_periods=drawdown_window).max()
    ratio = (close_panel / rolling_high).clip(0.0, 1.0)
    drawdown = ratio ** drawdown_concavity

    # Momentum (raw N-day return) — pct-rank applied at scoring time
    # (rank among eligible stocks, which depends on signal date)
    momentum_raw = close_panel / close_panel.shift(momentum_window) - 1.0

    return {
        "eligibility": eligibility,
        "persistence": persistence,
        "drawdown": drawdown,
        "momentum_raw": momentum_raw,
        "sma_short": sma_short,
        "sma_long": sma_long,
        "sma_persist_ref": sma_persist_ref_p,
    }


def make_tl25_score(panels: dict, *,
                    w_persistence: float = 1/3,
                    w_drawdown: float = 1/3,
                    w_momentum: float = 1/3,
                    regime_panel: Optional[pd.Series] = None,
                    bear_w_persistence: Optional[float] = None,
                    bear_w_drawdown: Optional[float] = None,
                    bear_w_momentum: Optional[float] = None,
                    candidate_fn=None):
    """Return a score_fn(signal_date) closure for use with run_strategy.

    If `regime_panel` is provided AND the bear_* weights are set, weights
    are tilted in bear regimes (analogous to OM25 v3). When all bear_*
    are None, the bull weights apply unconditionally.

    candidate_fn(date) -> set: optional point-in-time column mask (from
    scripts.universe_membership.make_candidate_fn). The momentum leg is
    pct-ranked among eligible stocks, so with an all-ever panel the
    eligible set must be date-masked or future universe additions with
    price history would shift pre-cutover ranks.
    """
    eligibility = panels["eligibility"]
    persistence = panels["persistence"]
    drawdown = panels["drawdown"]
    momentum_raw = panels["momentum_raw"]

    has_tilt = (
        regime_panel is not None
        and bear_w_persistence is not None
        and bear_w_drawdown is not None
        and bear_w_momentum is not None
    )

    def score_fn(signal_date, **_):
        if signal_date not in eligibility.index:
            return pd.Series(dtype=float)

        if has_tilt:
            try:
                rv = regime_panel.get(signal_date, True)
                is_bull = bool(rv) if rv is not None else True
            except Exception:
                is_bull = True
        else:
            is_bull = True

        if is_bull:
            wp, wd, wm = w_persistence, w_drawdown, w_momentum
        else:
            wp, wd, wm = bear_w_persistence, bear_w_drawdown, bear_w_momentum

        wsum = wp + wd + wm
        if wsum <= 0:
            return pd.Series(dtype=float)
        wp_n, wd_n, wm_n = wp / wsum, wd / wsum, wm / wsum

        elig_row = eligibility.loc[signal_date]
        if candidate_fn is not None:
            cands = candidate_fn(signal_date)
            elig_row = elig_row & elig_row.index.isin(cands)
        if not elig_row.any():
            return pd.Series(dtype=float)
        persist_row = persistence.loc[signal_date].fillna(0)
        dd_row = drawdown.loc[signal_date].fillna(0)
        mom_raw_row = momentum_raw.loc[signal_date]

        # Momentum: pct-rank among eligible only
        mom_eligible = mom_raw_row.where(elig_row).dropna()
        if len(mom_eligible) > 1 and wm > 0:
            mom_ranked = mom_eligible.rank(method="average", ascending=True)
            mom_pct = (mom_ranked - 1) / (len(mom_ranked) - 1)
            mom_pct_full = pd.Series(0.0, index=elig_row.index)
            mom_pct_full.loc[mom_pct.index] = mom_pct.values
        else:
            mom_pct_full = pd.Series(0.0, index=elig_row.index)

        # Composite (only on eligible stocks)
        weighted = (wp_n * persist_row + wd_n * dd_row + wm_n * mom_pct_full)
        weighted = weighted.where(elig_row)
        return weighted

    return score_fn
