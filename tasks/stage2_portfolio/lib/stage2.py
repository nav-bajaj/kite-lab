"""Stage 2 (Weinstein / Minervini trend-template) detection and scoring.

Two distinct pieces, deliberately separated:

  GATE   - a hard pass/fail stage-2 classification. A name is either in a
           confirmed advancing stage or it is not. This is the trend-template:
           full moving-average stack, rising long MA, position inside the
           52-week range, and relative strength vs the market.

  SCORE  - how to rank the names that pass. The production momentum books all
           rank by some flavour of trailing return; S2 deliberately does not.
           Its default rank is stage QUALITY: how young the advance is, how
           un-extended the price is, whether volatility is contracting, and
           whether volume shows accumulation. Trailing return enters only as
           a gate (RS) and, optionally, as one small scoring leg.

All windows use an explicit min_periods (~80% of window) - see
reference-panel-calendar-trap.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _mp(window: int, frac: float = 0.8) -> int:
    return max(2, int(window * frac))


def build_stage2_panels(close: pd.DataFrame, volume: pd.DataFrame, *,
                        sma_fast: int = 50,
                        sma_mid: int = 150,
                        sma_slow: int = 200,
                        slope_lookback: int = 20,
                        range_window: int = 252,
                        off_low_min: float = 0.30,
                        off_high_max: float = 0.25,
                        rs_window: int = 126,
                        rs_min_pct: float = 0.70,
                        vol_contraction_short: int = 21,
                        vol_contraction_long: int = 126,
                        accumulation_window: int = 50,
                        vol_trend_short: int = 50,
                        vol_trend_long: int = 200,
                        min_stage_age: int = 21,
                        require_volume_trend: bool = False) -> dict:
    """Pre-compute the stage-2 gate and every scoring input.

    Returns a dict of Date x Symbol panels. `gate` is the full stage-2
    classification (the entry-eligible set); `core_gate` is the price-structure
    half of it, used to age the advance without RS flicker resetting the clock.
    """
    sma_f = close.rolling(sma_fast, min_periods=_mp(sma_fast)).mean()
    sma_m = close.rolling(sma_mid, min_periods=_mp(sma_mid)).mean()
    sma_s = close.rolling(sma_slow, min_periods=_mp(sma_slow)).mean()

    hi = close.rolling(range_window, min_periods=_mp(range_window)).max()
    lo = close.rolling(range_window, min_periods=_mp(range_window)).min()

    # --- price-structure half of the trend template -------------------------
    c1 = (close > sma_m) & (close > sma_s)      # above the long MAs
    c2 = sma_m > sma_s                          # mid above slow
    c3 = sma_s > sma_s.shift(slope_lookback)    # slow MA rising ~1 month
    c4 = sma_f > sma_m                          # full stack
    c5 = close > sma_f                          # above the fast MA
    c6 = close >= lo * (1.0 + off_low_min)      # well off the 52w low
    c7 = close >= hi * (1.0 - off_high_max)     # near the 52w high
    core_gate = c1 & c2 & c3 & c4 & c5 & c6 & c7

    # --- how long the advance has been intact -------------------------------
    cg = core_gate.fillna(False)
    stage_age = _consecutive_true(cg)

    # --- relative strength (cross-sectional, IBD-style percentile) -----------
    ret_rs = close / close.shift(rs_window) - 1.0
    rs_pct = ret_rs.rank(axis=1, pct=True)

    # --- volume trend (participation expanding) -----------------------------
    v_short = volume.rolling(vol_trend_short, min_periods=_mp(vol_trend_short)).mean()
    v_long = volume.rolling(vol_trend_long, min_periods=_mp(vol_trend_long)).mean()
    vol_trend = v_short / v_long

    gate = core_gate & (rs_pct >= rs_min_pct) & (stage_age >= min_stage_age)
    if require_volume_trend:
        gate = gate & (vol_trend >= 1.0)

    # Weinstein's actual sell rule is far looser than his buy rule: a stage-2
    # advance ends when price loses the 30-week MA and that MA stops rising.
    # Requiring every entry condition to persist is what pins median hold at
    # ~21 days, so the hold gate is kept deliberately separate.
    hold_gate = (close > sma_m) & (sma_m >= sma_s)

    # Middle tier: the stage-2 STRUCTURE is intact even if price has slipped
    # under the 50 DMA or fallen out of the top quartile of its 52-week range.
    # Drops c5 (close > 50 DMA), c6/c7 (range position) and the RS screen,
    # keeps the moving-average stack and the rising 200 DMA.
    hold_gate_tiered = c1 & c2 & c3 & c4

    # --- scoring inputs -----------------------------------------------------
    rets = close.pct_change(fill_method=None)
    vol_s = rets.rolling(vol_contraction_short,
                         min_periods=_mp(vol_contraction_short)).std()
    vol_l = rets.rolling(vol_contraction_long,
                         min_periods=_mp(vol_contraction_long)).std()
    contraction = vol_s / vol_l

    up_vol = volume.where(rets > 0, 0.0)
    dn_vol = volume.where(rets < 0, 0.0)
    aw = accumulation_window
    up_sum = up_vol.rolling(aw, min_periods=_mp(aw)).sum()
    dn_sum = dn_vol.rolling(aw, min_periods=_mp(aw)).sum()
    accumulation = up_sum / dn_sum.replace(0.0, np.nan)

    extension = close / sma_f - 1.0

    return {
        "gate": gate.fillna(False),
        "hold_gate": hold_gate.fillna(False),
        "hold_gate_tiered": hold_gate_tiered.fillna(False),
        "core_gate": core_gate.fillna(False),
        "stage_age": stage_age,
        "rs_pct": rs_pct,
        "ret_rs": ret_rs,
        "contraction": contraction,
        "accumulation": accumulation,
        "extension": extension,
        "vol_trend": vol_trend,
        "sma_fast": sma_f,
        "sma_mid": sma_m,
        "sma_slow": sma_s,
        "hi_252": hi,
        "lo_252": lo,
    }


def _consecutive_true(mask: pd.DataFrame) -> pd.DataFrame:
    """Per column, count of consecutive True rows ending at each row."""
    m = mask.astype(int)
    csum = m.cumsum()
    # reset the running count at every False
    reset = csum.where(~mask.astype(bool)).ffill().fillna(0)
    return (csum - reset).where(mask.astype(bool), 0.0)


def _pct(series: pd.Series) -> pd.Series:
    """Percentile rank in [0,1]; constant/short inputs collapse to 0.5."""
    s = series.dropna()
    if len(s) < 2:
        return pd.Series(0.5, index=series.index)
    r = s.rank(method="average", ascending=True)
    out = (r - 1) / (len(r) - 1)
    return out.reindex(series.index).fillna(0.5)


# Pre-registered scoring variants. Weights are over the four quality legs plus
# the one momentum leg; each is percentile-ranked among gate-passers on the day.
VARIANTS = {
    # Control: trend template + rank purely by relative strength. Closest to
    # the production momentum books - included so the quality legs have to earn
    # their place against it.
    "A_rs": dict(w_freshness=0.0, w_unextended=0.0, w_contraction=0.0,
                 w_accumulation=0.0, w_rs=1.0),
    # The intended S2: rank by stage quality only, no return term at all.
    "B_quality": dict(w_freshness=0.25, w_unextended=0.25, w_contraction=0.25,
                      w_accumulation=0.25, w_rs=0.0),
    # Quality without the freshness leg - isolates what "buy it early" is worth.
    "C_nofresh": dict(w_freshness=0.0, w_unextended=1/3, w_contraction=1/3,
                      w_accumulation=1/3, w_rs=0.0),
    # Half quality, half RS.
    "D_blend": dict(w_freshness=0.125, w_unextended=0.125, w_contraction=0.125,
                    w_accumulation=0.125, w_rs=0.5),
    # Founder spec 2026-09-09: relative strength and un-extension only.
    "E_rs_unext": dict(w_freshness=0.0, w_unextended=0.5, w_contraction=0.0,
                       w_accumulation=0.0, w_rs=0.5),
}


def make_s2_score(panels: dict, *, w_freshness=0.25, w_unextended=0.25,
                  w_contraction=0.25, w_accumulation=0.25, w_rs=0.0,
                  candidate_fn=None, asymmetric_gate=False,
                  hold_mode="strict"):
    """Return score_fn(signal_date) -> Series for _clean_engine.run_strategy."""
    gate = panels["gate"]
    # hold_mode picks how loose the HOLD test is relative to the entry gate:
    #   strict - identical to entry (a name must keep qualifying outright)
    #   tiered - MA stack + rising 200 DMA only
    #   loose  - Weinstein's sell rule: above the 150 DMA, 150 above 200
    if asymmetric_gate or hold_mode != "strict":
        hold_gate = panels.get({"tiered": "hold_gate_tiered",
                                "loose": "hold_gate"}.get(hold_mode, "hold_gate"))
    else:
        hold_gate = None
    stage_age = panels["stage_age"]
    contraction = panels["contraction"]
    accumulation = panels["accumulation"]
    extension = panels["extension"]
    rs_pct_panel = panels["rs_pct"]

    weights = dict(freshness=w_freshness, unextended=w_unextended,
                   contraction=w_contraction, accumulation=w_accumulation,
                   rs=w_rs)
    wsum = sum(weights.values())
    if wsum <= 0:
        raise ValueError("S2 score weights sum to zero")
    weights = {k: v / wsum for k, v in weights.items()}

    def score_fn(signal_date, **_):
        if signal_date not in gate.index:
            return pd.Series(dtype=float)
        elig = gate.loc[signal_date]
        if hold_gate is not None:
            elig = elig | hold_gate.loc[signal_date]
        if candidate_fn is not None:
            cands = candidate_fn(signal_date)
            elig = elig & elig.index.isin(cands)
        if not elig.any():
            return pd.Series(dtype=float)
        cols = elig[elig].index

        total = pd.Series(0.0, index=cols)
        if weights["freshness"]:
            # younger advance ranks higher
            total += weights["freshness"] * (
                1.0 - _pct(stage_age.loc[signal_date, cols]))
        if weights["unextended"]:
            # closer to the 50 DMA ranks higher
            total += weights["unextended"] * (
                1.0 - _pct(extension.loc[signal_date, cols]))
        if weights["contraction"]:
            # tighter recent vol vs its own 6m vol ranks higher
            total += weights["contraction"] * (
                1.0 - _pct(contraction.loc[signal_date, cols]))
        if weights["accumulation"]:
            # more up-volume than down-volume ranks higher
            total += weights["accumulation"] * _pct(
                accumulation.loc[signal_date, cols])
        if weights["rs"]:
            total += weights["rs"] * _pct(rs_pct_panel.loc[signal_date, cols])

        return total.reindex(gate.columns)

    return score_fn
