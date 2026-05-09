"""OM25 stage-2 sweep at fixed 50/50 weights, lookback=252.

User decision: keep 50/50 score weights (CR-only is a separate defensive
product, not the main OM25). Pin lookback=252 (production default; 189
peak in IS may be overfit).

Vary remaining parameters to find best execution config:
- cadence: monthly, biweekly
- top_n × buffer: (20,15), (25,10), (25,15), (25,20), (30,15), (30,20)
- ATR stop: off, 4x, 5x
- return_filter: on, off
- min_obs: 220, 150

Limit: vary at most 2 dimensions away from baseline at a time. Cap ~25 configs.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

# Import the existing helpers from the main retune harness
from tasks.om25.experiments._om25_oos_retune import (
    make_om25_score, run_config, IS_END,
    PRICES_DIR, UNIVERSE, BENCHMARK,
)
from scripts._clean_engine import (
    fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe


BASELINE = dict(
    w_uc=0.5, w_cr=0.5,
    return_filter=True,
    lookback=252, min_obs=220,
    top_n=25, exit_buffer=15,
    cadence="monthly",
    atr_mult=0.0, atr_min_floor=0.0,
)


def vary(base: dict, **overrides) -> dict:
    return base | overrides


# Build grid: 2-dim variations from baseline
GRID = [
    BASELINE,  # 1 — base reference
]
# Cadence × top_n/buffer (no ATR) — 2 cadences × 6 (tn,bf) = 12 minus base = 11
for cadence in ("monthly", "biweekly"):
    for tn, bf in [(20, 15), (25, 10), (25, 15), (25, 20), (30, 15), (30, 20)]:
        cfg = vary(BASELINE, cadence=cadence, top_n=tn, exit_buffer=bf)
        if cfg != BASELINE:
            GRID.append(cfg)
# Cadence × ATR at top_n=25/bf=15: monthly+0 base, biweekly+0 already in above; add ATR variants
for cadence in ("monthly", "biweekly"):
    for atr in (4.0, 5.0):
        GRID.append(vary(BASELINE, cadence=cadence, atr_mult=atr))
# return_filter × min_obs at base
for rf in (True, False):
    for mo in (220, 150):
        cfg = vary(BASELINE, return_filter=rf, min_obs=mo)
        if cfg not in GRID:
            GRID.append(cfg)


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    out_dir = ROOT / f"experiments/oos_retune/{ts}_om25_50_50"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")
    print(f"[grid]    {len(GRID)} configs")

    print(f"\n[load] prices from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    universe = load_universe(UNIVERSE)
    cols = [c for c in close_panel.columns if c in universe]
    returns_uni = close_panel[cols].pct_change()

    weekly_fri = fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]

    rows = []
    t0 = time.time()
    for i, cfg in enumerate(GRID, 1):
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
        rows.append(out)
        elapsed = time.time() - t0
        print(f"  [{i:2d}/{len(GRID)}] cad={cfg['cadence']:>8s} "
              f"tn={cfg['top_n']:2d} bf={cfg['exit_buffer']:2d} "
              f"atr={cfg['atr_mult']} rf={cfg['return_filter']} mo={cfg['min_obs']}  "
              f"IS Sharpe={out.get('is_sharpe', 'NA'):>4}  "
              f"CAGR={out.get('is_cagr_pct', 'NA'):>5}%  "
              f"DD={out.get('is_max_dd_pct', 'NA'):>6}%  ({elapsed:.0f}s)")

    df = pd.DataFrame(rows).sort_values("is_sharpe", ascending=False)
    df.to_csv(out_dir / "stage2_50_50.csv", index=False)
    print(f"\n[wrote] {out_dir}/stage2_50_50.csv")
    print(f"\nTop 10 by IS Sharpe:")
    print(df.head(10)[["cadence","top_n","exit_buffer","atr_mult",
                       "return_filter","min_obs","is_sharpe","is_cagr_pct",
                       "is_max_dd_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
