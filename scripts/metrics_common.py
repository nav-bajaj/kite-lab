"""Single source of truth for portfolio performance metrics.

Used by the four daily-pipeline portfolio scripts
(run_om25_v3_portfolio, run_tl25_v3_portfolio, run_l6_v2_portfolio,
 run_combo_defensive_portfolio) to produce the dashboard
`momentum_metrics.csv` single-row summary.

Behavior is faithful to the inline implementations these scripts had
prior to consolidation:
  - CAGR uses 365.25-day years over calendar span
  - Annualized vol uses sqrt(252) on daily returns
  - Sharpe is (CAGR - rf) / vol with rf defaulting to 5%
  - Max drawdown is pv / pv.cummax() - 1, min
  - Hit rate is fraction of exits with pnl_pct > 0 (else 0)
  - Avg holding days from exits.hold_days mean (else 0)

Verified bit-identical against pre-consolidation outputs for all four
production portfolios (see tasks/pipeline_improvements/RESULTS.md
Validation Gate 1).

The legacy engines (backtest_momentum.summarise_metrics,
_clean_engine.compute_metrics) compute additional fields (sortino,
calmar, longest-DD-days) that this module deliberately omits — those
two functions are used by research/walk-forward paths and are out of
scope for the dashboard metrics file. Phase 3 of the refactor will
revisit unification once L6 legacy migrates to _clean_engine.
"""
from __future__ import annotations

import math
from typing import Optional

import pandas as pd


DEFAULT_RF_RATE = 0.05  # 5% annual risk-free, matching production convention
TRADING_DAYS_PER_YEAR = 252
DAYS_PER_YEAR = 365.25


def compute_dashboard_metrics(
    eq: pd.DataFrame,
    trades: pd.DataFrame,
    exits: pd.DataFrame,
    rf_rate: float = DEFAULT_RF_RATE,
) -> dict:
    """Compute the single-row dashboard metrics dict.

    Parameters
    ----------
    eq : DataFrame with columns ``date`` and ``portfolio_value``
        Daily equity curve. Must be sorted ascending by date.
    trades : DataFrame with column ``side`` (BUY/SELL) — only counts are read
    exits : DataFrame with optional columns ``pnl_pct``, ``hold_days``
    rf_rate : annual risk-free rate for Sharpe (default 5%)

    Returns
    -------
    dict with keys matching the on-disk schema of momentum_metrics.csv:
      start, end, total_return, cagr, max_drawdown, sharpe_ratio,
      annualized_volatility, hit_rate_overall, avg_holding_days,
      trades_total, buys, sells
    """
    pv = eq.set_index("date")["portfolio_value"].astype(float)
    rets = pv.pct_change().dropna()

    days = (pv.index[-1] - pv.index[0]).days
    yrs = max(days / DAYS_PER_YEAR, 1e-9)

    total_ret = pv.iloc[-1] / pv.iloc[0] - 1
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (cagr - rf_rate) / vol if vol > 0 else 0
    mdd = pv.div(pv.cummax()).min() - 1

    sells_mask = trades["side"] == "SELL"
    buys_mask = trades["side"] == "BUY"

    if not exits.empty and "pnl_pct" in exits.columns:
        hit_rate = (exits["pnl_pct"] > 0).mean()
    else:
        hit_rate = 0
    if not exits.empty and "hold_days" in exits.columns:
        avg_hold = exits["hold_days"].mean()
    else:
        avg_hold = 0

    return {
        "start": pv.index[0].date(),
        "end": pv.index[-1].date(),
        "total_return": float(total_ret),
        "cagr": float(cagr),
        "max_drawdown": float(mdd),
        "sharpe_ratio": float(sharpe),
        "annualized_volatility": float(vol),
        "hit_rate_overall": float(hit_rate),
        "avg_holding_days": float(avg_hold),
        "trades_total": int(len(trades)),
        "buys": int(buys_mask.sum()),
        "sells": int(sells_mask.sum()),
    }


def write_dashboard_metrics(
    dashboard_dir,
    eq: pd.DataFrame,
    trades: pd.DataFrame,
    exits: pd.DataFrame,
    rf_rate: float = DEFAULT_RF_RATE,
) -> dict:
    """Compute metrics and write to ``<dashboard_dir>/momentum_metrics.csv``.

    Returns the metrics dict (useful for log lines or further checks).
    """
    metrics = compute_dashboard_metrics(eq, trades, exits, rf_rate=rf_rate)
    pd.DataFrame([metrics]).to_csv(
        dashboard_dir / "momentum_metrics.csv", index=False,
    )
    return metrics
