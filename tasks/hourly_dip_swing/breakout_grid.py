"""Full-history breakout grid: channel x trail x short-lookback sleeves.

Addendum 2 ran only the 20d channel, no-stop, per the published-study
convention. This grid gives the breakout entry the same coverage the
dip got: Donchian channels 10/20/50d, exits with and without the 20%
trail, sleeves at 21td and 63td. Same engine, universe, window and
conventions as daily_lookback_grid.py (cap 25, cliff exclusion,
2010-06 -> 2026-08-21, fills next day OHLC/4 +/- 20bps).

Run:  .venv/bin/python tasks/hourly_dip_swing/breakout_grid.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols, donchian_upper, breakout_cross,
)
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402
from tasks.dip_vs_breakout_calls.experiment import (  # noqa: E402
    simulate, slot_curve, curve_metrics, group_stats, cadence, yearly,
    CLIFF_SYMBOLS, TAIL_START,
)

OUT_DIR = Path(__file__).resolve().parent
END = pd.Timestamp("2026-08-21")


def main():
    print("[bog] loading panels")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    keep = [c for c in panels["close"].columns if c not in CLIFF_SYMBOLS]
    close, trade, high = (panels["close"][keep], panels["trade"][keep],
                          panels["high"][keep])

    crosses = {ch: breakout_cross(close, donchian_upper(high, ch)).fillna(False)
               for ch in (10, 20, 50)}

    rows, yearlies = {}, {}
    for lb, lb_name in [(21, "1m"), (63, "3m")]:
        rank = build_score_rank(close, lb)
        for ch in (10, 20, 50):
            for use_ts20, exit_name in [(False, "xr"), (True, "ts20")]:
                name = f"bo{ch}_{lb_name}_{exit_name}"
                print(f"[bog] simulating {name}")
                calls, counts, skipped = simulate(
                    close, trade, crosses[ch], rank,
                    cap=25, end=END, use_ts20=use_ts20)
                calls.to_csv(OUT_DIR / f"calls_daily_{name}.csv", index=False)
                pv = slot_curve(calls, close, 25, END)
                tail = pv.loc[pv.index >= TAIL_START]
                tail = tail / tail.iloc[0]
                rows[name] = {**cadence(calls, END), **group_stats(calls),
                              **curve_metrics(pv),
                              **{f"tail_{k}": v
                                 for k, v in curve_metrics(tail).items()},
                              "mean_active": round(float(counts.mean()), 1),
                              "pct_days_full": round(
                                  float((counts >= 25).mean()) * 100, 1),
                              "skipped": skipped}
                yearlies[name] = yearly(calls, pv)

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.to_csv(OUT_DIR / "summary_breakout_grid.csv")
    (OUT_DIR / "report_breakout_grid.json").write_text(
        json.dumps({"arms": rows, "yearly": yearlies}, indent=2, default=str))
    pd.set_option("display.width", 300)
    show = ["calls_per_year", "pct_weeks_with_call", "n_closed", "n_open",
            "win_rate_pct", "mean_pnl_pct", "median_pnl_pct", "p5_pnl_pct",
            "p95_pnl_pct", "median_hold_td", "cagr_pct", "sharpe",
            "max_dd_pct", "tail_cagr_pct", "tail_sharpe", "tail_max_dd_pct",
            "mean_active", "pct_days_full"]
    print("\n=== breakout grid: channel x trail x 1m/3m sleeves ===")
    print(df[show].to_string())


if __name__ == "__main__":
    main()
