"""Compare the dip25_ts20 feed against production L6 v2 and OM25 v3
over the investor-sim window (2023-01-01 -> 2026-08-19).

L6 / OM25 configs are the h2 'base' variants (entries, scores, cadence,
sizing identical to the om25_alt harness, i.e. the docs/portfolios.md
baselines): L6 = NSE 500 weekly Thursday-signal top-24 rank exits;
OM25 = N250 biweekly Friday top-25, exit buffer 20, 20% trailing stop,
regime-tilted score. Same engine slippage (20bps).

Dip curve: investor sim gross (TAX_RATE=0), same slippage, same window.

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/compare_production.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (  # noqa: E402
    biweekly_fridays, fridays, thursdays, run_strategy,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.om25_v3 import (  # noqa: E402
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)

OUT_DIR = Path(__file__).resolve().parent
START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2026-08-19")


def metrics(pv):
    rets = pv.pct_change().dropna()
    years = (pv.index[-1] - pv.index[0]).days / 365.25
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return dict(cagr_pct=round(cagr * 100, 2),
                vol_pct=round(vol * 100, 2),
                sharpe=round((cagr - 0.05) / vol, 2),
                max_dd_pct=round(dd * 100, 2),
                calmar=round(float(cagr / abs(dd)), 2),
                total_mult=round(float(pv.iloc[-1] / pv.iloc[0]), 2))


def main():
    print("[cmp] engine panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma200 = close_panel.rolling(200, min_periods=200).mean()
    atr20 = close_panel.pct_change().rolling(20).std()

    nse500 = load_universe(ROOT / "data/static/nse500_universe.csv")
    n250 = load_universe(ROOT / "data/static/nifty250_universe.csv")
    nse500_cols = [s for s in close_panel.columns if s in nse500]
    n250_cols = [s for s in close_panel.columns if s in n250]

    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(L6_BASELINE["lookback_months"]),
        skip_days=L6_BASELINE["skip_days"])
    l6_score = make_momentum_score(
        l6_panels, vol_floor=L6_BASELINE["vol_floor"],
        vol_power=L6_BASELINE["vol_power"],
        cross_sectional_zscore=L6_BASELINE["cross_sectional_zscore"])

    regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar)
    om25_score = make_om25_tilt_score(
        close_panel[n250_cols].pct_change(), regime,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"])

    curves = {}
    for label, score_fn, cadence, min_hold, exit_buf, top_n, stop, use_stop in [
        ("L6 v2", l6_score, "weekly_thu", L6_BASELINE["min_hold_days"], 0, 24, 0.0, False),
        ("OM25 v3", om25_score, "biweekly", 0, 20, 25, 0.20, True),
    ]:
        if cadence == "biweekly":
            all_e, weekly = biweekly_fridays(calendar), fridays(calendar)
        else:
            all_e = weekly = thursdays(calendar)
        entry = all_e[(all_e >= START) & (all_e <= END)]
        wk = weekly[(weekly >= START) & (weekly <= END)]
        print(f"[cmp] running {label}")
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark,
            entry_signal_dates=entry, weekly_signal_dates=wk,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma200, atr_20_panel=atr20,
            top_n=top_n, exit_buffer=exit_buf,
            max_weight=0.075, slippage=0.002,
            atr_mult=0.0, atr_min_floor=stop,
            use_trailing_stop=use_stop, use_dma_exit=False,
            weekly_rank_check=False,
            regime_panel=None, bear_exposure=0.0, bear_skips_entries=False,
            min_hold_days=min_hold, initial_capital=1_000_000)
        eq = res["equity"].copy()
        eq["date"] = pd.to_datetime(eq["date"])
        pv = eq.set_index("date")["pv"].astype(float)
        curves[label] = pv[(pv.index >= START) & (pv.index <= END)]
        n_buys = int((res["trades"]["side"] == "BUY").sum())
        yrs = (curves[label].index[-1] - curves[label].index[0]).days / 365.25
        print(f"  buys/yr: {n_buys/yrs:.0f}")

    dip = pd.read_csv(OUT_DIR / "investor_gross_curve.csv",
                      parse_dates=["date"]).set_index("date")["equity"]
    dip_net = pd.read_csv(OUT_DIR / "investor_curve.csv",
                          parse_dates=["date"]).set_index("date")["equity"]
    curves["Dip feed (gross)"] = dip
    curves["Dip feed (25% FY tax)"] = dip_net

    b = pd.read_csv(ROOT / "indices_data/NIFTY_500.csv",
                    parse_dates=["date"]).set_index("date")["close"]
    curves["Nifty 500"] = b[(b.index >= START) & (b.index <= END)]

    rows = {k: metrics(v) for k, v in curves.items()}
    df = pd.DataFrame(rows).T
    print("\n=== 2023-01-01 -> 2026-08-19 ===")
    print(df.to_string())

    # daily-return correlations
    rets = pd.DataFrame({k: v.pct_change() for k, v in curves.items()}).dropna()
    daily_corr = rets.corr().round(3)
    print("\n=== daily-return correlation ===")
    print(daily_corr.round(2).to_string())
    daily_corr.to_csv(OUT_DIR / "correlation_daily.csv")

    # monthly-return correlations -- the decision-relevant view for a
    # diversification claim; daily co-movement overstates how much two
    # portfolios actually share over a holding period
    mrets = pd.DataFrame({k: v.resample("ME").last().pct_change()
                          for k, v in curves.items()}).dropna()
    monthly_corr = mrets.corr().round(3)
    print(f"\n=== monthly-return correlation (n={len(mrets)} months) ===")
    print(monthly_corr.round(2).to_string())
    monthly_corr.to_csv(OUT_DIR / "correlation_monthly.csv")

    # calendar-year returns
    print("\n=== calendar-year returns (%) ===")
    yr = pd.DataFrame({k: v.resample("YE").last().pct_change(fill_method=None)
                       .mul(100).round(1) for k, v in curves.items()})
    first = pd.Series({k: round((v.resample('YE').last().iloc[0] / v.iloc[0] - 1) * 100, 1)
                       for k, v in curves.items()}, name=yr.index[0])
    yr.iloc[0] = first
    yr.index = yr.index.year
    print(yr.to_string())

    df.to_csv(OUT_DIR / "production_comparison.csv")


if __name__ == "__main__":
    main()
