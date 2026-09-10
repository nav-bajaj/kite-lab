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
