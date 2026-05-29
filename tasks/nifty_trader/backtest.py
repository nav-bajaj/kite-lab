"""Single-instrument directional backtest engine for the Nifty trader.

Models a strategy that holds a continuous position in [-1.0, +1.0] (fraction
of capital) on the Nifty 50 index, rebalanced daily based on a signal
function. Tracks:

  - Position state at each date
  - Position-weighted daily P&L (return × position_yesterday)
  - Per-trade explicit cost (debited from P&L when |Δposition| > 0)
  - Monthly roll cost (debited on the last trading day of each calendar month)

This is intentionally simpler than the multi-asset FIFO portfolio engine
used by the production strategies — single instrument, no per-stock lot
accounting, just position × return arithmetic. The cost model lives in
`cost_model.py` and applies futures-equivalent rates.

Look-ahead safety:
  - Signal at date t is computed from data through t (EOD).
  - The position decided at t is held FROM t+1, applying t+1 to t+2 return.
  - Equivalently: position_yesterday × today's return → today's P&L.
  - The engine enforces this by shifting positions one day before applying.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    initial_capital: float = 2_500_000   # ₹25L (above 1-lot futures threshold)
    explicit_cost_bps_per_rt: float = 5.0  # 5 bps round-trip explicit
    roll_cost_bps_per_month: float = 10.0  # 10 bps monthly roll (futures only)
    apply_roll_cost: bool = True
    long_cap: float = 1.0
    short_cap: float = -0.5
    name: str = "untitled"


@dataclass
class BacktestResult:
    config: BacktestConfig
    nifty: pd.Series                   # input nifty close
    position: pd.Series                # position decided EOD t (applied to t+1)
    position_lagged: pd.Series         # position held during day t (for P&L)
    daily_ret_nifty: pd.Series         # Nifty's daily return
    daily_ret_strat_gross: pd.Series   # strategy daily return BEFORE costs
    daily_cost: pd.Series              # explicit + roll costs each day (as fraction)
    daily_ret_strat_net: pd.Series     # after costs
    equity: pd.Series                  # cumulative post-cost equity curve in ₹
    bh_equity: pd.Series               # Nifty buy-and-hold curve (₹) for compare
    n_trades: int = 0
    total_explicit_cost: float = 0.0
    total_roll_cost: float = 0.0

    @property
    def years(self) -> float:
        return (self.equity.index[-1] - self.equity.index[0]).days / 365.25

    @property
    def cagr(self) -> float:
        if self.years <= 0:
            return 0.0
        return (self.equity.iloc[-1] / self.equity.iloc[0]) ** (1.0 / self.years) - 1.0

    @property
    def bh_cagr(self) -> float:
        if self.years <= 0:
            return 0.0
        return (self.bh_equity.iloc[-1] / self.bh_equity.iloc[0]) ** (1.0 / self.years) - 1.0

    @property
    def vol(self) -> float:
        return float(self.daily_ret_strat_net.std() * np.sqrt(252))

    @property
    def sharpe(self) -> float:
        if self.vol == 0:
            return 0.0
        return float(self.daily_ret_strat_net.mean() * 252 / self.vol)

    @property
    def max_drawdown(self) -> float:
        eq = self.equity
        peak = eq.cummax()
        dd = eq / peak - 1.0
        return float(dd.min())

    @property
    def bh_max_drawdown(self) -> float:
        eq = self.bh_equity
        peak = eq.cummax()
        dd = eq / peak - 1.0
        return float(dd.min())

    @property
    def calmar(self) -> float:
        return self.cagr / abs(self.max_drawdown) if self.max_drawdown != 0 else 0.0

    @property
    def time_in_position(self) -> dict:
        p = self.position_lagged.fillna(0)
        n = len(p)
        return {
            "long": float((p > 0).sum() / n),
            "short": float((p < 0).sum() / n),
            "flat": float((p == 0).sum() / n),
        }


def run_backtest(
    nifty_close: pd.Series,
    signal_fn: Callable[[pd.Series, pd.DataFrame], pd.Series],
    feature_panel: pd.DataFrame,
    config: BacktestConfig,
) -> BacktestResult:
    """Run a backtest.

    signal_fn(nifty_close, feature_panel) -> pd.Series of target positions
       (continuous in [config.short_cap, config.long_cap]), indexed by date.
       Will be clipped to caps and lagged 1 day before applying.
    """
    nifty = nifty_close.sort_index()
    target_pos = signal_fn(nifty, feature_panel).reindex(nifty.index).fillna(0.0)
    target_pos = target_pos.clip(lower=config.short_cap, upper=config.long_cap)

    # Lag: position decided EOD t applies to t+1's return
    position_lagged = target_pos.shift(1).fillna(0.0)
    daily_ret_nifty = nifty.pct_change(fill_method=None).fillna(0.0)
    daily_ret_strat_gross = position_lagged * daily_ret_nifty

    # Trade events: |delta position| × explicit_cost_per_unit_traded
    # explicit_cost_bps_per_rt is round-trip (entry + exit) for moving 100% of
    # capital. Half = one-way cost per unit of |Δposition|.
    delta_pos = target_pos.diff().abs().fillna(target_pos.abs())  # first day counts as a fresh entry
    trade_cost_rate = config.explicit_cost_bps_per_rt / 10_000.0
    explicit_cost = delta_pos * (trade_cost_rate / 2.0)  # half rate per leg

    # Monthly roll cost: applied on last trading day of each month, sized by
    # |position held that day|. Only if config.apply_roll_cost.
    monthly_marker = nifty.index.to_series().groupby(
        [nifty.index.year, nifty.index.month]
    ).transform("max")
    is_month_end = nifty.index.to_series() == monthly_marker
    roll_rate = config.roll_cost_bps_per_month / 10_000.0
    roll_cost = (
        position_lagged.abs() * roll_rate * is_month_end.astype(float).values
        if config.apply_roll_cost else pd.Series(0.0, index=nifty.index)
    )

    daily_cost = explicit_cost + roll_cost
    daily_ret_strat_net = daily_ret_strat_gross - daily_cost

    equity = config.initial_capital * (1.0 + daily_ret_strat_net).cumprod()
    bh_equity = config.initial_capital * (1.0 + daily_ret_nifty).cumprod()

    n_trades = int((delta_pos > 1e-9).sum())

    return BacktestResult(
        config=config,
        nifty=nifty,
        position=target_pos,
        position_lagged=position_lagged,
        daily_ret_nifty=daily_ret_nifty,
        daily_ret_strat_gross=daily_ret_strat_gross,
        daily_cost=daily_cost,
        daily_ret_strat_net=daily_ret_strat_net,
        equity=equity,
        bh_equity=bh_equity,
        n_trades=n_trades,
        total_explicit_cost=float(explicit_cost.sum() * config.initial_capital),
        total_roll_cost=float(roll_cost.sum() * config.initial_capital),
    )


def print_summary(res: BacktestResult, *, header: str | None = None) -> None:
    if header:
        print(f"\n=== {header} ===")
    tip = res.time_in_position
    print(f"  Period:       {res.equity.index[0].date()} → {res.equity.index[-1].date()}  ({res.years:.1f}y)")
    print(f"  Final equity: ₹{res.equity.iloc[-1]/1e6:.2f}M  (from ₹{res.config.initial_capital/1e6:.2f}M)")
    print(f"  Strategy:     CAGR {res.cagr*100:>6.2f}%  Sharpe {res.sharpe:>5.2f}  "
          f"MaxDD {res.max_drawdown*100:>6.2f}%  Calmar {res.calmar:>4.2f}  Vol {res.vol*100:>5.2f}%")
    print(f"  Nifty B&H:    CAGR {res.bh_cagr*100:>6.2f}%  MaxDD {res.bh_max_drawdown*100:>6.2f}%")
    print(f"  Time in:      long {tip['long']*100:.0f}%  short {tip['short']*100:.0f}%  flat {tip['flat']*100:.0f}%")
    print(f"  Trades:       {res.n_trades:,}  ·  total explicit ₹{res.total_explicit_cost/1e5:.2f}L  "
          f"·  total roll ₹{res.total_roll_cost/1e5:.2f}L")
