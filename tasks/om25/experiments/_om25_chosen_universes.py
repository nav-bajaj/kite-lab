"""OM25 chosen config across 3 universes × 2 cadences (IS=2009-2016).

Candidate config from 50/50 stage-2 review:
  - 50/50 weights (UC + CR)
  - lookback=252, min_obs=220
  - top_n=25, exit_buffer=20
  - return_filter=ON
  - no ATR stop
  - max_weight=7.5%, slippage=20bps

Runs across NSE 500 / Nifty 250 / Nifty 100 in monthly + biweekly cadences.
Reports IS metrics for each combination.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tasks.om25.experiments._om25_oos_retune import (
    make_om25_score, run_config, IS_END,
    PRICES_DIR, BENCHMARK,
)
from scripts._clean_engine import (
    fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe


CHOSEN = dict(
    w_uc=0.5, w_cr=0.5,
    return_filter=True,
    lookback=252, min_obs=220,
    top_n=25, exit_buffer=20,
    atr_mult=0.0, atr_min_floor=0.0,
)

UNIVERSES = [
    ("NSE 500",  ROOT / "data/static/nse500_universe.csv"),
    ("Nifty 250", ROOT / "data/static/nifty250_universe.csv"),
    ("Nifty 100", ROOT / "data/static/nifty100_universe.csv"),
]
CADENCES = ["monthly", "biweekly"]


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    out_dir = ROOT / f"experiments/oos_retune/{ts}_om25_universes"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")

    print(f"\n[load] prices from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_fri = fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]

    rows = []
    t0 = time.time()
    for univ_name, univ_path in UNIVERSES:
        universe = load_universe(univ_path)
        cols = [c for c in close_panel.columns if c in universe]
        if len(cols) == 0:
            print(f"  [{univ_name}] no overlap with panel — skipping")
            continue
        returns_uni = close_panel[cols].pct_change()
        print(f"\n[{univ_name}] {len(cols)} symbols in panel")

        for cadence in CADENCES:
            cfg = CHOSEN | dict(cadence=cadence)
            out = run_config(
                returns_uni=returns_uni, close_panel=close_panel,
                trade_panel=trade_panel, calendar=calendar,
                benchmark_aligned=benchmark_aligned,
                sma_200=sma_200, atr_20=atr_20,
                weekly_filt=weekly_filt,
                monthly_first=monthly_first, biweekly_fri=biweekly_fri,
                cfg=cfg, is_only=True,
            )
            out.pop("_equity", None)
            out["universe"] = univ_name
            out["univ_size"] = len(cols)
            rows.append(out)
            elapsed = time.time() - t0
            print(f"  {cadence:>8s}  IS Sharpe={out.get('is_sharpe', 'NA'):>4}  "
                  f"CAGR={out.get('is_cagr_pct', 'NA'):>5}%  "
                  f"DD={out.get('is_max_dd_pct', 'NA'):>6}%  ({elapsed:.0f}s)")

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "by_universe.csv", index=False)

    print(f"\n=== Comparison: 50/50 + 252 + top-25/buf-20 + RF on, by universe × cadence ===")
    pivot = df.pivot_table(
        index="universe", columns="cadence",
        values=["is_sharpe", "is_cagr_pct", "is_max_dd_pct"],
    )
    print(pivot.to_string())
    print(f"\n[wrote] {out_dir}/by_universe.csv")


if __name__ == "__main__":
    main()
