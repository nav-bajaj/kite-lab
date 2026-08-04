"""Regime-filter overlay test: Nifty 500 42-day rolling return < 0 -> cash.

Rule under test
---------------
- Signal: rolling 42-trading-day total return of NIFTY 500 close.
  Negative -> "risk-off" (no invest), non-negative -> "risk-on".
- Confirmation: the regime state only flips after 3 consecutive days of
  the opposite raw signal (hysteresis, mirrors OM25 v3's confirm_days=3).
- Execution: state decided at close of day t applies from day t+1.

Method
------
Overlay on the production backtest equity curves (daily returns). When
risk-off, the portfolio sits in cash (0% daily return). Each switch pays
one-way slippage of 0.2% (engine's slippage=0.002) - full liquidation on
exit, full re-buy on entry. This approximates re-running the engine with
a hard regime gate; it ignores second-order effects (re-entry picks a
fresh top-N, drawdown stops interact with the gate).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
NIFTY500 = ROOT / "indices_data" / "NIFTY_500.csv"

PORTFOLIOS = {
    "Quality Momentum (OM25 v3)": ROOT
    / "data/om25_v3_portfolios/om25_v3_portfolio_20260721_163735/om25_equity.csv",
    "Defensive Blend (COMBO)": ROOT
    / "data/combo_defensive_portfolios/combo_defensive_portfolio_20260721_163805/combo_equity.csv",
}

LOOKBACK = 42
CONFIRM = 3
SLIPPAGE = 0.002  # one-way, matches engine config
RF = 0.05  # to match sharpe_rf5 in production metrics.json


def build_regime(close: pd.Series, lookback: int, confirm: int) -> pd.Series:
    """True = risk-on. Flip only after `confirm` consecutive opposite days."""
    roll_ret = close / close.shift(lookback) - 1.0
    raw_on = roll_ret >= 0
    state = []
    cur = True  # start invested
    streak = 0
    for dt, on in raw_on.items():
        if pd.isna(roll_ret.loc[dt]):
            state.append(cur)
            continue
        if on != cur:
            streak += 1
            if streak >= confirm:
                cur = on
                streak = 0
        else:
            streak = 0
        state.append(cur)
    return pd.Series(state, index=close.index, name="risk_on")


def metrics(pv: pd.Series, rf: float = RF) -> dict:
    ret = pv.pct_change().dropna()
    years = (pv.index[-1] - pv.index[0]).days / 365.25
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = ret.std() * np.sqrt(252)
    sharpe = (cagr - rf) / vol if vol > 0 else np.nan
    dd = (pv / pv.cummax() - 1).min()
    return {
        "end_value": round(pv.iloc[-1]),
        "total_return_pct": round((pv.iloc[-1] / pv.iloc[0] - 1) * 100, 1),
        "cagr_pct": round(cagr * 100, 2),
        "vol_pct": round(vol * 100, 2),
        "sharpe_rf5": round(sharpe, 2),
        "max_dd_pct": round(dd * 100, 2),
    }


def off_windows(state: pd.Series) -> list[tuple[str, str, int]]:
    out = []
    off_start = None
    prev_dt = None
    for dt, on in state.items():
        if not on and off_start is None:
            off_start = dt
        elif on and off_start is not None:
            n = state.loc[off_start:prev_dt].shape[0]
            out.append((str(off_start.date()), str(prev_dt.date()), n))
            off_start = None
        prev_dt = dt
    if off_start is not None:
        n = state.loc[off_start:].shape[0]
        out.append((str(off_start.date()), str(state.index[-1].date()), n))
    return out


def main() -> None:
    idx = pd.read_csv(NIFTY500, parse_dates=["date"], index_col="date")
    regime = build_regime(idx["close"], LOOKBACK, CONFIRM)

    report: dict = {
        "config": {
            "lookback_days": LOOKBACK,
            "confirm_days": CONFIRM,
            "slippage_per_switch": SLIPPAGE,
            "signal_index": "NIFTY 500",
        },
        "portfolios": {},
    }

    for name, path in PORTFOLIOS.items():
        eq = pd.read_csv(path, parse_dates=["date"], index_col="date")
        pv = eq["pv"]
        ret = pv.pct_change().fillna(0.0)

        # state at close of t-1 governs exposure on day t
        exposed = regime.reindex(pv.index).ffill().shift(1).fillna(True)

        filt_ret = ret.where(exposed, 0.0)
        # pay slippage on every state change (sell-all or buy-all)
        switches = exposed.astype(int).diff().abs().fillna(0)
        filt_ret = filt_ret - switches * SLIPPAGE
        filt_pv = pv.iloc[0] * (1 + filt_ret).cumprod()

        # what the portfolio itself did while we sat in cash
        avoided = (1 + ret.where(~exposed, 0.0)).prod() - 1

        state_in_range = regime.reindex(pv.index).ffill()
        wins = off_windows(state_in_range)

        report["portfolios"][name] = {
            "period": f"{pv.index[0].date()} -> {pv.index[-1].date()}",
            "baseline": metrics(pv),
            "with_filter": metrics(filt_pv),
            "n_switches": int(switches.sum()),
            "pct_days_in_cash": round((~exposed).mean() * 100, 1),
            "portfolio_return_while_in_cash_pct": round(avoided * 100, 1),
            "off_windows": wins,
        }

        out_csv = Path(__file__).parent / f"filtered_equity_{name.split('(')[1].strip(')').replace(' ', '_').lower()}.csv"
        pd.DataFrame({"pv_baseline": pv, "pv_filtered": filt_pv, "exposed": exposed}).to_csv(out_csv)

    out = Path(__file__).parent / "overlay_results.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
