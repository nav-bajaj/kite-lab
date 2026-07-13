"""Composite 0-100 scores + insight tags (C3 of insights_v2).

Four transparent, auditable scores plus a set of pure-observation insight
tags. Every weight below is a documented design choice — they are quoted
verbatim in the Learn explainers, so the scoring must stay simple and
inspectable, never a fitted black box.

All scores are a weighted checklist of sub-signals, each mapped to [0, 1],
blended, then ×100. When a sub-signal's input is missing the component is
dropped and the remaining weights are renormalized, so a partial record
still yields a score on the same 0-100 scale (or None if nothing is
available). This keeps every score monotone in each of its own drivers.

  Trend Score (higher = stronger uptrend structure)
    0.40 position   fraction of 20/50/100/200-DMA the close sits above
    0.20 alignment  50-DMA above 200-DMA (golden structure)
    0.15 slope      50/200-DMA rising over the last 20 sessions
    0.15 proximity  closeness to the 52-week high (0 at -25% or worse)
    0.10 drawdown   control of the trailing-1y max drawdown (0 at -50%)

  Extension Risk (higher = more stretched vs history; a RISK score)
    0.35 dist above 20-DMA in ATR units (0 at/below, 1 at +6 ATR)
    0.25 dist above 50-DMA in ATR units (0 at/below, 1 at +10 ATR)
    0.20 trailing-5d return percentile vs the stock's own year
    0.20 RSI(14) overbought lean (0 at 50, 1 at 100)
    Bands: Low <25, Moderate <50, High <75, Very high ≥75.

  Volume Confirmation (higher = stronger participation)
    0.45 today's volume ratio (0 at ≤1x, 1 at ≥3x the prior-20 avg)
    0.30 5-day volume ratio (0 at ≤1x, 1 at ≥2.5x the 20d avg)
    0.25 up/down-day volume balance (0 at ≤1x, 1 at ≥3x)
    Bands: Weak <33, Neutral <66, Strong ≥66.

  Momentum Consistency (higher = smoother, more durable trend)
    0.45 fraction of positive weeks over the trailing 6 months
    0.30 control of the trailing-6m max drawdown (0 at -30%)
    0.25 vol-adjusted 6m return (6m return ÷ 60d annualized vol, 0 at ≤0,
         1 at ≥2)

Insight tags are observations only (no forward-return claim). The exact
strings are compliance-controlled and covered by the closed-lexicon test.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from app.insights.rs_rank import RSEntry
from app.insights.stock_metrics import StockMetrics

# Insight-tag strings — EXACT wording is compliance-controlled. Any change
# must go through tests/test_insights_commentary.py (closed lexicon).
TAG_MOMENTUM_LEADER = "Momentum leader"
TAG_NEAR_52W_HIGH = "Near 52-week high"
TAG_FRESH_52W_HIGH = "Fresh 52-week high"
TAG_VOLUME_EXPANSION = "Volume expansion"
TAG_EXTENDED = "Extended"
TAG_COILED = "Coiled"
TAG_NEW_MOMENTUM = "New momentum"
TAG_QUIET = "Quiet"

# Full compliance surface — every user-facing label these engines emit.
# The closed-lexicon test (tests/test_insights_commentary.py) locks this set
# so no tag/band label can ship without passing the no-recommendation-verb /
# no-jargon gate. The C4/C5 API/UI agent should render only these strings.
INSIGHT_TAGS: tuple[str, ...] = (
    TAG_MOMENTUM_LEADER, TAG_NEAR_52W_HIGH, TAG_FRESH_52W_HIGH,
    TAG_VOLUME_EXPANSION, TAG_EXTENDED, TAG_COILED, TAG_NEW_MOMENTUM, TAG_QUIET,
)
EXTENSION_BANDS: tuple[str, ...] = ("Low", "Moderate", "High", "Very high")
VOLUME_BANDS: tuple[str, ...] = ("Weak", "Neutral", "Strong")

# Tag thresholds (transparent design choices).
MOMENTUM_LEADER_PCTILE = 90.0     # RS top decile
NEAR_52W_HIGH_PCT = -0.03         # within 3% below the high
VOLUME_EXPANSION_RATIO = 2.0      # ≥2x the prior-20 average
QUIET_VOL_PCTILE = 0.25           # bottom-quartile realized vol


@dataclass
class StockScores:
    symbol: str
    trend_score: float | None
    extension_risk: float | None
    extension_band: str | None
    volume_confirmation: float | None
    volume_band: str | None
    momentum_consistency: float | None
    tags: tuple[str, ...]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = list(self.tags)
        return d


# ─────────────────────────── helpers ───────────────────────────

def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _blend(components: list[tuple[float, float | None]]) -> float | None:
    """Weighted blend over available (weight, sub_score) pairs; sub_score
    in [0,1] or None (dropped). Renormalizes over present weights. ×100."""
    num = 0.0
    den = 0.0
    for w, v in components:
        if v is None:
            continue
        num += w * _clamp01(v)
        den += w
    if den == 0:
        return None
    return round(100.0 * num / den, 2)


def extension_band(score: float) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Moderate"
    if score < 75:
        return "High"
    return "Very high"


def volume_band(score: float) -> str:
    if score < 33:
        return "Weak"
    if score < 66:
        return "Neutral"
    return "Strong"


def _atr_units_above(close, sma, atr) -> float | None:
    if close is None or sma is None or atr is None or atr <= 0:
        return None
    return max(0.0, (close - sma) / atr)


# ─────────────────────────── the four scores ───────────────────────────

def _trend_score(m: StockMetrics) -> float | None:
    position = None
    flags = [m.above_20dma, m.above_50dma, m.above_100dma, m.above_200dma]
    known = [f for f in flags if f is not None]
    if known:
        position = sum(1 for f in known if f) / len(known)
    alignment = None if m.dma_50_above_200 is None else (
        1.0 if m.dma_50_above_200 else 0.0)
    slope = None
    slopes = [m.slope_50dma_20d, m.slope_200dma_20d]
    kn = [s for s in slopes if s is not None]
    if kn:
        slope = sum(1.0 for s in kn if s > 0) / len(kn)
    proximity = None
    if m.dist_52w_high_pct is not None:
        # dist is ≤0; 0 at the high, 0 at -25% or worse
        proximity = _clamp01(1.0 - (-m.dist_52w_high_pct) / 0.25)
    ddctrl = None
    if m.max_drawdown_1y_pct is not None:
        ddctrl = _clamp01(1.0 - (-m.max_drawdown_1y_pct) / 0.50)
    return _blend([
        (0.40, position), (0.20, alignment), (0.15, slope),
        (0.15, proximity), (0.10, ddctrl),
    ])


def _extension_risk(m: StockMetrics) -> float | None:
    e20 = _atr_units_above(m.close, m.sma_20, m.atr_14)
    e50 = _atr_units_above(m.close, m.sma_50, m.atr_14)
    c20 = None if e20 is None else _clamp01(e20 / 6.0)
    c50 = None if e50 is None else _clamp01(e50 / 10.0)
    r5 = m.ret_5d_pctile_1y
    rsi = None if m.rsi_14 is None else _clamp01((m.rsi_14 - 50.0) / 50.0)
    return _blend([(0.35, c20), (0.25, c50), (0.20, r5), (0.20, rsi)])


def _volume_confirmation(m: StockMetrics) -> float | None:
    today = None if m.vol_ratio is None else _clamp01((m.vol_ratio - 1.0) / 2.0)
    five = None if m.vol_ratio_5d is None else _clamp01((m.vol_ratio_5d - 1.0) / 1.5)
    ud = None if m.updown_vol_ratio_20d is None else \
        _clamp01((m.updown_vol_ratio_20d - 1.0) / 2.0)
    return _blend([(0.45, today), (0.30, five), (0.25, ud)])


def _momentum_consistency(m: StockMetrics) -> float | None:
    pos = m.pct_positive_weeks_6m
    ddctrl = None
    if m.max_drawdown_6m_pct is not None:
        ddctrl = _clamp01(1.0 - (-m.max_drawdown_6m_pct) / 0.30)
    vadj = None
    if m.ret_6m is not None and m.vol_60d_annualized is not None \
            and m.vol_60d_annualized > 0:
        vadj = _clamp01((m.ret_6m / m.vol_60d_annualized) / 2.0)
    return _blend([(0.45, pos), (0.30, ddctrl), (0.25, vadj)])


# ─────────────────────────── tags ───────────────────────────

def _tags(m: StockMetrics, rs: RSEntry | None, ext_band: str | None,
          is_coiled: bool, is_inflection_top25: bool) -> tuple[str, ...]:
    tags: list[str] = []
    if rs is not None and rs.percentile is not None \
            and rs.percentile >= MOMENTUM_LEADER_PCTILE:
        tags.append(TAG_MOMENTUM_LEADER)
    if m.fresh_52w_high:
        tags.append(TAG_FRESH_52W_HIGH)
    elif m.dist_52w_high_pct is not None \
            and NEAR_52W_HIGH_PCT <= m.dist_52w_high_pct <= 0.0:
        tags.append(TAG_NEAR_52W_HIGH)
    if m.vol_ratio is not None and m.vol_ratio >= VOLUME_EXPANSION_RATIO:
        tags.append(TAG_VOLUME_EXPANSION)
    if ext_band in ("High", "Very high"):
        tags.append(TAG_EXTENDED)
    if is_coiled:
        tags.append(TAG_COILED)
    if is_inflection_top25:
        tags.append(TAG_NEW_MOMENTUM)
    if m.vol_percentile_1y is not None \
            and m.vol_percentile_1y <= QUIET_VOL_PCTILE and m.above_200dma:
        tags.append(TAG_QUIET)
    return tuple(tags)


def compute_scores(
    m: StockMetrics,
    rs: RSEntry | None = None,
    is_coiled: bool = False,
    is_inflection_top25: bool = False,
) -> StockScores:
    """Pure scoring over one StockMetrics record (+ optional RS + flags)."""
    ext = _extension_risk(m)
    vol = _volume_confirmation(m)
    ext_band = extension_band(ext) if ext is not None else None
    vol_bnd = volume_band(vol) if vol is not None else None
    return StockScores(
        symbol=m.symbol,
        trend_score=_trend_score(m),
        extension_risk=ext,
        extension_band=ext_band,
        volume_confirmation=vol,
        volume_band=vol_bnd,
        momentum_consistency=_momentum_consistency(m),
        tags=_tags(m, rs, ext_band, is_coiled, is_inflection_top25),
    )


# ─────────────────────────── frame builder + cache ───────────────────────────

_MEM_CACHE: dict[str, dict[str, StockScores]] = {}


def get_scores(asof=None) -> dict[str, StockScores]:
    """Scores for every symbol as of `asof`, cached per resolved date.

    Composes stock_metrics + rs_rank + the reused coiled-spring detector
    and the inflection cohort. Empty dict if the panel is unavailable.
    """
    import pandas as pd

    from app.insights import rs_rank, stock_metrics, watchlists

    from app.insights import sector_constituents as _sc

    metrics = stock_metrics.get_stock_metrics(asof)
    if not metrics:
        return {}
    date_key = next(iter(metrics.values())).date
    # Fold the source signature into the key so a same-date data update
    # (adjusted closes, refreshed constituents) reloads instead of serving a
    # stale composite.
    sig = stock_metrics._panel_signature() + _sc._signature()
    key = f"{date_key}|{stock_metrics._sig_token(sig)}"
    if key in _MEM_CACHE:
        return _MEM_CACHE[key]

    resolved = pd.Timestamp(date_key)
    rs_table = rs_rank.get_rs_table(resolved)
    inflection = {e.symbol for e in
                  rs_rank.get_live_inflection_cohort(resolved, top_n=25)}
    # Reuse the existing coiled-spring detector (no duplication) — membership
    # of a full-universe run is the per-stock "coiled" flag.
    coiled = {e.symbol for e in
              watchlists.get_coiled_springs(resolved, limit=len(metrics))}

    out: dict[str, StockScores] = {}
    for sym, m in metrics.items():
        out[sym] = compute_scores(
            m, rs=rs_table.get(sym),
            is_coiled=sym in coiled,
            is_inflection_top25=sym in inflection,
        )
    _MEM_CACHE[key] = out
    return out


def clear_cache() -> None:
    _MEM_CACHE.clear()
