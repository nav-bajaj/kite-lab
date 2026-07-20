"""Export aligned series for the Momentum Crowding Index chart.

Dumps a compact JSON the explainer artifact embeds: for each weekly date,
the crowding index (absolute), its expanding percentile, NIFTY 100 (rebased
to 100), and the L6 momentum-portfolio equity (rebased to 100). Lets us eye
the crowding ebbs/flows against price.

Run:  python tasks/raam_transplant/chart_data.py > /dev/null   (writes JSON)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._clean_engine import run_strategy, thursdays  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6, build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from residuals import build_residual_panel, avg_pairwise_corr  # noqa: E402
from e1_l6div import load_index_close, NSE500_UNIVERSE_CSV, NIFTY100_INDEX  # noqa: E402

INDEX_TOPK = 50
CROWD_WINDOW = 63
START = "2010-01-01"
END = "2026-07-20"
OUT = ROOT / "tasks/raam_transplant/chart_series.json"


def main():
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in nse500]
    nifty100 = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()

    l6_panels = build_momentum_panels(close_panel[cols], lookback_days=lookback_months_to_days(L6["lookback_months"]), skip_days=L6["skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=L6["vol_floor"], vol_power=L6["vol_power"], cross_sectional_zscore=L6["cross_sectional_zscore"])
    momentum = l6_panels["momentum"]
    resid = build_residual_panel(close_panel[cols], nifty100)["residual"]

    rebal = thursdays(calendar)
    rebal = rebal[(rebal >= pd.Timestamp(START)) & (rebal <= pd.Timestamp(END))]

    # crowding index
    idx = {}
    for d in rebal:
        mrow = momentum.loc[d].dropna() if d in momentum.index else pd.Series(dtype=float)
        top = mrow.sort_values(ascending=False).head(INDEX_TOPK).index
        win = resid.loc[:d].tail(CROWD_WINDOW)[[t for t in top if t in resid.columns]]
        idx[d] = avg_pairwise_corr(win)
    index = pd.Series(idx).dropna()
    exp_pct = pd.Series({d: float((index.loc[:d] <= index.loc[d]).mean()) for d in index.index})

    # L6 equity
    ed = rebal
    res = run_strategy(
        close_panel=close_panel[cols], trade_panel=trade_panel[cols], calendar=calendar,
        benchmark_aligned=benchmark, entry_signal_dates=ed, weekly_signal_dates=ed,
        signal_function=l6_score, signal_function_args={}, sma_200_panel=sma_200[cols], atr_20_panel=atr_20[cols],
        top_n=24, exit_buffer=0, max_weight=0.075, slippage=0.002, atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False, weekly_rank_check=False, regime_panel=None,
        bear_exposure=0.0, bear_skips_entries=False, min_hold_days=8, initial_capital=1_000_000)
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    l6_pv = eq.set_index("date")["pv"].astype(float)

    # align to the weekly index dates, rebase price series to 100 at first date
    dates = index.index
    n100 = nifty100.reindex(dates).ffill()
    l6w = l6_pv.reindex(dates).ffill()
    n100_base = n100.iloc[0]; l6_base = l6w.iloc[0]

    series = []
    for d in dates:
        series.append({
            "d": str(d.date()),
            "c": round(float(index.loc[d]), 4),
            "p": round(float(exp_pct.loc[d]) * 100, 1),
            "n": round(float(n100.loc[d] / n100_base * 100), 1),
            "l": round(float(l6w.loc[d] / l6_base * 100), 1),
        })
    OUT.write_text(json.dumps({
        "meta": {"topk": INDEX_TOPK, "window": CROWD_WINDOW, "start": str(dates[0].date()),
                 "end": str(dates[-1].date()), "n": len(series),
                 "current_crowding": round(float(index.iloc[-1]), 4),
                 "current_pctile": round(float(exp_pct.iloc[-1]) * 100, 1)},
        "series": series,
    }))
    print(f"wrote {OUT} with {len(series)} weekly points")


if __name__ == "__main__":
    main()
