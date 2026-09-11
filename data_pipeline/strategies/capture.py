"""Capture-statistics score for the rebuild.

Per stock over a trailing `lookback`-session window of daily returns:
  UC = mean stock return on market-up days / mean market return on those days
  DC = the same on market-down days
  CR = UC / DC
Market = equal-weight mean return of the signal-date members across the
window (founder's choice (b), 2026-09-10). Each metric is percentile-ranked
across eligible stocks; the score is a weighted blend of the two ranks.

Eligibility: at least `min_obs` returns in the window; optionally a
positive window total return (`return_filter`, a searchable switch). The
old rule requiring >= 50 up and >= 50 down days is gone (brief). It can be
re-enabled with `legacy_updown_rule=True` for the smoke test only.

Regimes: with `regime_panel=None` the bull weights apply always (one
regime). With a panel, bear dates use the bear weights (two regimes).
"""
from __future__ import annotations

import pandas as pd


def make_capture_score(returns_universe: pd.DataFrame, regime_panel: pd.Series | None, *,
                       w_uc_bull: float, w_cr_bull: float, w_uc_bear: float = 0.0, w_cr_bear: float = 1.0,
                       return_filter: bool = True, lookback: int = 252, min_obs: int = 220,
                       candidate_fn=None, legacy_updown_rule: bool = False, mom_quantile: float = 0.0):
    """mom_quantile > 0 (founder, 2026-09-10): restrict eligibility to the top `mom_quantile` share of stocks by window
    total return before the capture ratios are ranked, e.g. 0.25 = top quartile of momentum over the same lookback."""
    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback:
            return pd.Series(dtype=float)
        is_bull = True
        if regime_panel is not None:
            rv = regime_panel.get(signal_date, True)
            is_bull = bool(rv) if rv is not None and rv == rv else True
        w_uc, w_cr = (w_uc_bull, w_cr_bull) if is_bull else (w_uc_bear, w_cr_bear)
        if w_uc + w_cr <= 0:
            return pd.Series(dtype=float)
        w_uc, w_cr = w_uc / (w_uc + w_cr), w_cr / (w_uc + w_cr)
        window = returns_universe.iloc[idx - lookback + 1:idx + 1]
        if candidate_fn is not None:
            cands = candidate_fn(signal_date)
            window = window[[c for c in window.columns if c in cands]]
        market = window.mean(axis=1)
        up, dn = market > 0, market < 0
        mu_up, mu_dn = market[up].mean(), market[dn].mean()
        if not (mu_up > 0) or not (mu_dn < 0):
            return pd.Series(dtype=float)
        n_obs = window.notna().sum()
        elig = n_obs >= min_obs
        if return_filter:
            elig &= ((1 + window.fillna(0)).prod() - 1) > 0
        if legacy_updown_rule:
            elig &= (window.notna() & up.values[:, None]).sum() >= 50
            elig &= (window.notna() & dn.values[:, None]).sum() >= 50
        if mom_quantile > 0:
            tot = ((1 + window.fillna(0)).prod() - 1)[elig.values]
            if len(tot) == 0:
                return pd.Series(dtype=float)
            elig &= (((1 + window.fillna(0)).prod() - 1) >= tot.quantile(1 - mom_quantile))
        cols = window.columns[elig.values]
        if len(cols) == 0:
            return pd.Series(dtype=float)
        w = window[cols]
        uc = w[up].mean() / mu_up
        dc = w[dn].mean() / mu_dn
        cr = uc / dc.where(dc > 0)
        cr = cr.fillna(uc)
        df = pd.DataFrame({"up": uc, "ratio": cr}).dropna()
        if df.empty:
            return pd.Series(dtype=float)
        up_pct = df["up"].rank(method="average") / len(df)
        cr_pct = df["ratio"].rank(method="average") / len(df)
        return w_uc * up_pct + w_cr * cr_pct
    return score_fn
