"""ROC regime with confirmation hysteresis — the brief's only risk control.

  roc    = close / close.shift(n) - 1      on the regime index
  risk-on when roc > 0 (threshold zero, as in tasks/portfolio_risk_2026)
  state flips to bear only after `confirm_days` consecutive risk-off
  readings, back to bull only after `confirm_days` consecutive risk-on
  readings; lagged one session so a day's close acts from the next day.
The MA variant is kept for the smoke test only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _confirm(raw: pd.Series, confirm_days: int) -> pd.Series:
    n_on = raw.astype(float).where(raw.notna()).rolling(confirm_days, min_periods=confirm_days).sum()
    state, out = True, []
    for v in n_on.values:
        if np.isnan(v):
            out.append(state); continue
        if state and v == 0:
            state = False
        elif not state and v == confirm_days:
            state = True
        out.append(state)
    return pd.Series(out, index=raw.index, dtype=bool)


def _load(idx_path) -> pd.Series:
    df = pd.read_csv(idx_path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    return df.sort_values("date").set_index("date")["close"]


def roc_regime(idx_path, n: int, confirm_days: int, calendar=None) -> pd.Series:
    s = _load(idx_path)
    roc = s / s.shift(n) - 1.0
    raw = (roc > 0).astype(float)
    raw[roc.isna()] = np.nan
    r = _confirm(raw, confirm_days).shift(1)
    return r.reindex(calendar).ffill() if calendar is not None else r


def ma_regime(idx_path, window: int, confirm_days: int, calendar=None) -> pd.Series:
    s = _load(idx_path)
    ma = s.rolling(window, min_periods=window).mean()
    raw = (s > ma).astype(float); raw[ma.isna()] = np.nan
    r = _confirm(raw, confirm_days).shift(1)
    return r.reindex(calendar).ffill() if calendar is not None else r


# ---------------------------------------------------------------------------
# §3j — momentum-strength regime. Every indicator is a daily series built
# from the harness close panel and point-in-time membership; the weak state
# is "indicator below threshold", confirmed with the same hysteresis as ROC
# and lagged one session. Thresholds are absolute or an expanding-window
# quantile of the indicator's own history at or before t.
# ---------------------------------------------------------------------------
from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(0, "/Users/navdeep/kite-lab"); _sys.path.insert(0, "/Users/navdeep/kite-lab/scripts")
from scripts.universe_membership import load_membership as _load_membership  # noqa: E402

STRENGTH_KINDS = ("breadth", "breadth_ma", "disp", "factor", "leaders", "persist", "capture",
                  "breadth_d", "capture_d", "leaders_d")


def membership_mask(mem_path, close: pd.DataFrame) -> pd.DataFrame:
    """Date x Symbol bool: symbol is a member on that date (from inclusive, to exclusive)."""
    df = _load_membership(_Path(mem_path))
    mask = pd.DataFrame(False, index=close.index, columns=close.columns)
    idx = mask.index
    for sym, f, t in df[["symbol", "effective_from", "effective_to"]].itertuples(index=False):
        if sym not in mask.columns:
            continue
        sel = idx >= f
        if pd.notna(t):
            sel &= idx < t
        mask.loc[sel, sym] = True
    return mask


def _rowwise_corr(a: pd.DataFrame, b: pd.DataFrame) -> pd.Series:
    v = a.notna() & b.notna()
    a, b = a.where(v), b.where(v)
    am, bm = a.sub(a.mean(axis=1), axis=0), b.sub(b.mean(axis=1), axis=0)
    num = (am * bm).sum(axis=1)
    den = np.sqrt((am ** 2).sum(axis=1) * (bm ** 2).sum(axis=1))
    return (num / den.where(den > 0)).where(v.sum(axis=1) >= 50)


def strength_indicator(close: pd.DataFrame, mask: pd.DataFrame, kind: str, length: int, min_members: int = 100) -> pd.Series:
    """Daily momentum-strength reading. `close` must already be cut at the run end."""
    if kind.endswith("_d"):
        base = strength_indicator(close, mask, kind[:-2], 252, min_members)
        return base - base.shift(length)
    ret = close.pct_change(fill_method=None)
    if kind == "breadth":
        r = close / close.shift(length) - 1.0
        pos = (r > 0).astype(float).where(r.notna() & mask)
        return pos.mean(axis=1).where(pos.count(axis=1) >= min_members)
    if kind == "breadth_ma":
        ma = close.rolling(length, min_periods=length).mean()
        above = (close > ma).astype(float).where(ma.notna() & close.notna() & mask)
        return above.mean(axis=1).where(above.count(axis=1) >= min_members)
    if kind == "disp":
        r = (close / close.shift(length) - 1.0).where(mask)
        q = r.quantile([0.25, 0.75], axis=1).T
        return (q[0.75] - q[0.25]).where(r.count(axis=1) >= min_members)
    mom = (close.shift(21) / close.shift(252) - 1.0).where(mask)
    pct = mom.rank(axis=1, pct=True)
    if kind in ("factor", "leaders"):
        held = pct.shift(1)                                   # ranks as of the prior close
        top = ret.where(held >= 0.9).mean(axis=1)
        if kind == "factor":
            daily = top - ret.where(held <= 0.1).mean(axis=1)
        else:
            daily = top - ret.where(mask).mean(axis=1)        # winners vs the equal-weight universe
        daily = daily.where(pct.count(axis=1) >= min_members)
        return daily.rolling(length, min_periods=length).sum()
    if kind == "persist":
        return _rowwise_corr(pct, pct.shift(length))
    if kind == "capture":
        rm = ret.where(mask)
        mkt = rm.mean(axis=1)
        up, dn = (mkt > 0).values[:, None], (mkt < 0).values[:, None]
        ru, rd = rm.where(np.broadcast_to(up, rm.shape)), rm.where(np.broadcast_to(dn, rm.shape))
        mp = max(length // 4, 10)
        su, sd = ru.rolling(length, min_periods=mp).mean(), rd.rolling(length, min_periods=mp).mean()
        mu_up = mkt.where(mkt > 0).rolling(length, min_periods=mp).mean()
        mu_dn = mkt.where(mkt < 0).rolling(length, min_periods=mp).mean()
        uc, dc = su.div(mu_up, axis=0), sd.div(mu_dn, axis=0)
        cr = (uc / dc.where(dc > 0)).fillna(uc)
        enough = rm.rolling(length, min_periods=1).count() >= int(0.87 * length)
        cr = cr.where(enough & mask)
        return cr.quantile(0.9, axis=1).where(cr.count(axis=1) >= min_members)
    raise ValueError(f"unknown strength kind {kind}")


def strength_regime(ind: pd.Series, thresh: float, mode: str, confirm_days: int, calendar) -> pd.Series:
    """True = normal, False = weak (cut exposure). `mode` 'abs': ind >= thresh;
    'pct': ind >= the `thresh`-quantile of its own expanding history (min 252 obs)."""
    level = ind.expanding(min_periods=252).quantile(thresh) if mode == "pct" else pd.Series(thresh, index=ind.index)
    raw = (ind >= level).astype(float)
    raw[ind.isna() | level.isna()] = np.nan
    r = _confirm(raw, confirm_days).shift(1)
    r = r.reindex(calendar).ffill()
    return r.fillna(True).infer_objects(copy=False).astype(bool)
