"""Portfolio-crowding engine — how clustered a book is once beta is stripped.

A momentum book can hold 24 different tickers that are really one bet: a
theme (PSU / defence / smallcap) the whole book has piled into. Raw price
correlation can't tell that apart from shared market beta. So crowding is
measured on MARKET-RESIDUAL returns: strip each name's trailing-252d
NIFTY-100 beta, then take the mean off-diagonal pairwise correlation of
the residuals over a trailing window. High = the names move together for
reasons beyond the market = a concentrated theme bet.

The reading is an OBSERVATION, not a prediction: research
(tasks/raam_transplant) found crowding weakly predicts near-term drawdown
(Spearman ~-0.19), too weak to carry a forward-return claim. So the engine
reports the level and a null-distribution percentile ("more clustered than
X% of random same-size books right now") and nothing about future returns.

All windows are trailing-only (no lookahead). Pure-function core; the
loader/API wiring lives separately.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_returns(close_panel: pd.DataFrame) -> pd.DataFrame:
    return close_panel.pct_change()


def rolling_beta(returns: pd.DataFrame, market_returns: pd.Series, *,
                 window: int = 252, min_periods: int = 200) -> pd.DataFrame:
    """Time-varying OLS beta of each column vs the market, trailing `window`."""
    m = market_returns.reindex(returns.index)
    mean_m = m.rolling(window, min_periods=min_periods).mean()
    var_m = (m * m).rolling(window, min_periods=min_periods).mean() - mean_m ** 2
    mean_r = returns.rolling(window, min_periods=min_periods).mean()
    mean_rm = returns.mul(m, axis=0).rolling(window, min_periods=min_periods).mean()
    cov = mean_rm.sub(mean_r.mul(mean_m, axis=0))
    return cov.div(var_m.replace(0, np.nan), axis=0)


def residual_panel(close_panel: pd.DataFrame, market_close: pd.Series, *,
                   beta_window: int = 252, min_periods: int = 200) -> pd.DataFrame:
    """Market-residual daily returns: r_i - beta_i(t) * r_market(t)."""
    r = daily_returns(close_panel)
    m = market_close.pct_change()
    beta = rolling_beta(r, m, window=beta_window, min_periods=min_periods)
    m_aligned = m.reindex(r.index)
    return r.sub(beta.mul(m_aligned, axis=0))


def book_crowding(residual: pd.DataFrame, holdings, as_of, *,
                  window: int = 63, min_obs: int = 40) -> float:
    """Mean off-diagonal pairwise correlation of the holdings' residual
    returns over the `window` trading days ending at `as_of`.

    Returns NaN if fewer than two holdings have >= min_obs valid observations
    in the window.
    """
    held = [h for h in holdings if h in residual.columns]
    if len(held) < 2:
        return float("nan")
    block = residual[held].loc[:as_of].tail(window).dropna(axis=1, thresh=min_obs)
    if block.shape[1] < 2:
        return float("nan")
    c = block.corr().values
    iu = np.triu_indices(c.shape[0], k=1)
    vals = c[iu]
    vals = vals[~np.isnan(vals)]
    return float(np.mean(vals)) if len(vals) else float("nan")


def crowding_null_percentile(residual: pd.DataFrame, holdings, universe, as_of, *,
                             window: int = 63, min_obs: int = 40,
                             n_draws: int = 500, seed: int = 0) -> float:
    """Percentile (0-1) of the book's crowding within a null distribution of
    random same-size books drawn from `universe`.

    0.90 means the book is more clustered than 90% of random books of the
    same size, measured on the same window. Deterministic given `seed`.
    Returns NaN if the book crowding itself is undefined.
    """
    held = [h for h in holdings if h in residual.columns]
    book_c = book_crowding(residual, held, as_of, window=window, min_obs=min_obs)
    if np.isnan(book_c):
        return float("nan")

    pool = [s for s in universe if s in residual.columns]
    k = len(held)
    if len(pool) <= k:
        return float("nan")

    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_draws):
        pick = list(rng.choice(pool, size=k, replace=False))
        c = book_crowding(residual, pick, as_of, window=window, min_obs=min_obs)
        if not np.isnan(c):
            draws.append(c)
    if not draws:
        return float("nan")
    draws = np.asarray(draws)
    return float((draws <= book_c).mean())
