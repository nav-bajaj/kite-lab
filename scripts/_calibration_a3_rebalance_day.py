"""A3: Test rebalance day-of-week alignment. The new engine's `_clean_engine`
uses Friday signals (→ Monday exec); the legacy engine uses Thursday signals
(→ Friday exec). Re-run the new engine's production config with Thursday
signals and see if the legacy numbers come closer.

If the gap closes substantially, day-of-week is the source. If not, look at
position-sizing logic next (A2).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._momentum_engine import (
    BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts._clean_engine import (
    run_strategy, fridays, thursdays,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics
import math


def run_with_signal_day(close_panel, trade_panel, calendar, benchmark_aligned,
                          sma_200, atr_20, close_uni, signal_day: str,
                          window_start="2020-07-10", window_end="2026-05-08"):
    """Run production config with the given signal day-of-week."""
    cfg = BASELINE.copy()
    panels = build_momentum_panels(
        close_uni,
        lookback_days=lookback_months_to_days(cfg["lookback_months"]),
        skip_days=cfg["skip_days"],
    )
    score_fn = make_momentum_score(
        panels, vol_floor=cfg["vol_floor"], vol_power=cfg["vol_power"],
        cross_sectional_zscore=True,
    )
    # Entry dates: thursdays or fridays
    if signal_day == "thursday":
        entry_all = thursdays(calendar)
    else:
        entry_all = fridays(calendar)
    weekly_filt = fridays(calendar)  # weekly exit checks stay Fridays
    s = pd.Timestamp(window_start); e = pd.Timestamp(window_end)
    entry_dates = entry_all[(entry_all >= s) & (entry_all <= e)]
    weekly_filt = weekly_filt[(weekly_filt >= s) & (weekly_filt <= e)]

    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        max_weight=cfg["max_weight"], slippage=cfg["slippage"],
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
        weekly_rank_check=False,
        regime_panel=None, bear_exposure=0.0,
        min_hold_days=cfg["min_hold_days"],
        initial_capital=1_000_000,
    )
    return res


def metric(res, start, end, label):
    eq = res["equity"]
    m = period_metrics(eq, label, start, end)
    cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
    pv = eq["pv"].astype(float)
    rets = pv.pct_change().dropna()
    ann_vol = float(rets.std() * math.sqrt(252)) if len(rets) > 1 else None
    sharpe_rf5 = ((cagr - 5) / (ann_vol * 100)
                  if cagr is not None and ann_vol and ann_vol > 0 else None)
    return {
        "label": label,
        "cagr_pct": cagr, "sharpe_rf0": sh, "sharpe_rf5_cagr": sharpe_rf5,
        "vol_pct": ann_vol * 100 if ann_vol else None,
        "max_dd_pct": dd, "n_trades": len(res["trades"]),
        "n_exits": len(res["exits"]),
    }


def main():
    print("[load] nse500_data (production data dir) ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_universe(ROOT / BASELINE["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  {len(cols)} symbols")

    print("\n[run] new engine, Friday signal day (current default) ...")
    res_fri = run_with_signal_day(close_panel, trade_panel, calendar,
                                    benchmark_aligned, sma_200, atr_20,
                                    close_uni, signal_day="friday")
    m_fri = metric(res_fri, "2020-07-10", "2026-05-08", "Friday signals")

    print("[run] new engine, Thursday signal day (legacy convention) ...")
    res_thu = run_with_signal_day(close_panel, trade_panel, calendar,
                                    benchmark_aligned, sma_200, atr_20,
                                    close_uni, signal_day="thursday")
    m_thu = metric(res_thu, "2020-07-10", "2026-05-08", "Thursday signals")

    print(f"\n{'=' * 90}")
    print("A3: PRODUCTION config, new engine, Friday vs Thursday signals")
    print(f"  Reference legacy production: 52.82% CAGR / 1.83 Sharpe (rf=5%) / -29.27% DD")
    print(f"{'=' * 90}")
    df = pd.DataFrame([m_fri, m_thu])
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
