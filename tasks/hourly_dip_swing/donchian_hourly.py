"""Hourly Donchian breakout into short-lookback momentum sleeves.

Follow-up to experiment.py (hourly dip swing): same healed hourly panel,
same slot engine, but the entry timer is a Donchian breakout (close
crosses above the prior N-bar high) and the momentum sleeve uses 1-month
(21td) and 3-month (63td) lookbacks instead of the production 126td.

Arms: channel N in {35, 70, 140} bars (5/10/20 sessions), trail 8/12%
plus a wide-20% diagnostic, for each momentum lookback. Benchmarks:
daily 20d-breakout bo25 (no stop, momentum-decay exit) with the same
21/63td ranks on the same window.

Run:  .venv/bin/python tasks/hourly_dip_swing/donchian_hourly.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, donchian_upper, breakout_cross,
)
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402
from tasks.dip_vs_breakout_calls.experiment import (  # noqa: E402
    simulate as simulate_daily, slot_curve as slot_curve_daily, group_stats,
)
from tasks.hourly_dip_swing.experiment import (  # noqa: E402
    load_hourly_panels, heal_hourly, hourly_rank_matrix, simulate_hourly,
    slot_curve_hourly, curve_metrics_hourly, hourly_stats,
    HOURLY_DIR, START,
)

OUT_DIR = Path(__file__).resolve().parent
END_D = pd.Timestamp("2026-08-21")

# mid-day split-switch artifacts found by experiment.py's detector
EXCLUDE = {"ANGELONE", "ECLERX", "IRB", "LICI", "METROPOLIS"}


def main():
    print("[dch] loading daily panels (merged, healed)")
    panels_d = load_ohlc_panels()
    close_d, trade_d = panels_d["close"], panels_d["trade"]

    hourly_syms = sorted(p.name.replace("_60minute.csv", "")
                         for p in HOURLY_DIR.glob("*_60minute.csv"))
    syms = [s for s in hourly_syms if s in close_d.columns and s not in EXCLUDE]
    print(f"[dch] {len(syms)} symbols after artifact exclusion")

    print("[dch] loading + healing hourly panels")
    panels_h = load_hourly_panels(syms)
    hcols = panels_h["close"].columns
    panels_h, heal_log = heal_hourly(panels_h, close_d[hcols])
    print(f"[dch] healed {len(heal_log)} symbol-days")

    hclose = panels_h["close"]
    hhigh = panels_h["high"]
    htrade = (panels_h["open"] + panels_h["high"]
              + panels_h["low"] + panels_h["close"]) / 4.0

    close_b, trade_b = close_d[list(hcols)], trade_d[list(hcols)]
    high_b = panels_d["high"][list(hcols)]

    rows = {}
    for lb, lb_name in [(21, "1m"), (63, "3m")]:
        rank_d = build_score_rank(close_b, lb)
        rank_v = hourly_rank_matrix(rank_d, hclose.index, hcols)

        for n_bars, trail, tag in [
            (35, 0.08, "ch5s_ts8"),
            (70, 0.08, "ch10s_ts8"),
            (70, 0.12, "ch10s_ts12"),
            (140, 0.12, "ch20s_ts12"),
            (140, 0.20, "ch20s_ts20"),
        ]:
            name = f"h_{lb_name}_{tag}"
            print(f"[dch] simulating {name}")
            upper = donchian_upper(hhigh, n_bars)
            cross = breakout_cross(hclose, upper).fillna(False)
            calls, counts, skipped = simulate_hourly(
                hclose, htrade, cross, rank_v, cap=25, trail=trail)
            calls.to_csv(OUT_DIR / f"calls_{name}.csv", index=False)
            pv = slot_curve_hourly(calls, hclose, 25)
            rows[name] = {**hourly_stats(calls, counts, 25, skipped),
                          **curve_metrics_hourly(pv)}

        # daily benchmark: 20d breakout, cap 25, momentum-decay exit only
        bench_name = f"daily_bo25_{lb_name}"
        print(f"[dch] benchmark {bench_name}")
        cross_d = breakout_cross(close_b, donchian_upper(high_b, 20)).fillna(False)
        calls_d, counts_d, _ = simulate_daily(
            close_b, trade_b, cross_d, rank_d, cap=25,
            end=END_D, use_ts20=False, start=START)
        calls_d.to_csv(OUT_DIR / f"calls_{bench_name}.csv", index=False)
        pv_d = slot_curve_daily(calls_d, close_b, 25, END_D, start=START)
        rets = pv_d.pct_change().dropna()
        years = (pv_d.index[-1] - pv_d.index[0]).days / 365.25
        cagr = pv_d.iloc[-1] ** (1 / years) - 1
        vol = rets.std() * math.sqrt(252)
        dd = (pv_d / pv_d.cummax() - 1).min()
        rows[bench_name] = {
            **group_stats(calls_d),
            "window_ret_pct": round((pv_d.iloc[-1] - 1) * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "max_dd_pct": round(dd * 100, 2),
            "calls_per_year": round(
                len(calls_d[calls_d.status == "closed"]) / years, 1),
            "mean_active": round(float(counts_d.mean()), 1)}

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.to_csv(OUT_DIR / "summary_donchian.csv")
    (OUT_DIR / "report_donchian.json").write_text(
        json.dumps(rows, indent=2, default=str))
    pd.set_option("display.width", 300)
    show = ["calls_per_year", "pct_weeks_with_call", "n_closed", "n_open",
            "win_rate_pct", "mean_pnl_pct", "median_pnl_pct", "p5_pnl_pct",
            "p95_pnl_pct", "median_hold_sessions", "window_ret_pct",
            "cagr_pct", "sharpe", "max_dd_pct", "mean_active"]
    print("\n=== hourly donchian breakout, 1m/3m momentum sleeves ===")
    print(df[[c for c in show if c in df.columns]].to_string())


if __name__ == "__main__":
    main()
