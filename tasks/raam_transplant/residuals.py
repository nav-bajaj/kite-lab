"""Beta-residual return panel — the crowding instrument for raam_transplant.

Among 500 stocks that all carry NIFTY beta, ranking on raw pairwise
correlation just re-selects low-beta defensives (the LV25 "too defensive"
attractor from tasks/om25_alt). So crowding is measured on MARKET-RESIDUAL
returns: strip each stock's trailing-252d NIFTY-100 beta, then correlate
the residuals. That isolates shared theme/sector exposure from beta.

All windows are trailing-only (no lookahead): beta at day t uses returns
through t; the residual at t uses beta_t and the market return at t.

Reusable by the diagnostic (Phase 0), E1 selection penalty (Phase 1), and
RC25's C component (Phase 3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_returns(close_panel: pd.DataFrame) -> pd.DataFrame:
    return close_panel.pct_change()


def rolling_beta(returns: pd.DataFrame, market_returns: pd.Series, *,
                 window: int = 252, min_periods: int = 200) -> pd.DataFrame:
    """Time-varying OLS beta of each column vs the market, trailing `window`.

    beta_t = cov(r, m)_t / var(m)_t, both rolling means over the window.
    Vectorised across all symbols at once.
    """
    m = market_returns.reindex(returns.index)
    mean_m = m.rolling(window, min_periods=min_periods).mean()
    var_m = (m * m).rolling(window, min_periods=min_periods).mean() - mean_m ** 2
    mean_r = returns.rolling(window, min_periods=min_periods).mean()
    mean_rm = returns.mul(m, axis=0).rolling(window, min_periods=min_periods).mean()
    cov = mean_rm.sub(mean_r.mul(mean_m, axis=0))
    beta = cov.div(var_m.replace(0, np.nan), axis=0)
    return beta


def residual_returns(returns: pd.DataFrame, market_returns: pd.Series,
                     beta: pd.DataFrame) -> pd.DataFrame:
    m = market_returns.reindex(returns.index)
    return returns.sub(beta.mul(m, axis=0))


def build_residual_panel(close_panel: pd.DataFrame, market_close: pd.Series, *,
                         beta_window: int = 252, min_periods: int = 200) -> dict:
    """Returns {returns, market_returns, beta, residual} panels."""
    r = daily_returns(close_panel)
    m = market_close.pct_change()
    beta = rolling_beta(r, m, window=beta_window, min_periods=min_periods)
    resid = residual_returns(r, m, beta)
    return {"returns": r, "market_returns": m, "beta": beta, "residual": resid}


def avg_pairwise_corr(resid_window: pd.DataFrame, *, min_obs: int = 40) -> float:
    """Mean off-diagonal pairwise correlation of a days×symbols residual block.

    A high value = the names move together once market beta is stripped =
    the book is crowded into a shared theme. Columns with < min_obs valid
    observations are dropped before correlating.
    """
    block = resid_window.dropna(axis=1, thresh=min_obs)
    if block.shape[1] < 2:
        return np.nan
    c = block.corr()
    n = c.shape[0]
    iu = np.triu_indices(n, k=1)
    vals = c.values[iu]
    vals = vals[~np.isnan(vals)]
    return float(np.mean(vals)) if len(vals) else np.nan
