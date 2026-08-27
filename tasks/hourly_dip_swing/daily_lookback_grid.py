"""Full-history daily grid: breakout + dip entries over 1m/3m/6m sleeves.

Answers the follow-up from the hourly probes: daily_bo25 on a 1-month
momentum sleeve looked outstanding on the 10-month hourly window
(+23%, 150 calls/yr) — does the short-lookback sleeve survive the full
2010-06 -> 2026-08-21 history, for both entry styles?

Faithful reuse of the dip_vs_breakout_calls engine and conventions:
same universe (nse500_data_merged, cliff symbols excluded), same
execution (signal at close, fill next day OHLC/4 +/- 20bps), cap 25,
momentum-rank slot priority, exit at momentum rank < 0.35. Breakout
arms run without a stop, dip arms with the 20% trail — the winning
exit per entry style from the published grid. The 126td arms re-run
here so all six rows share one window and dataset.

Run:  .venv/bin/python tasks/hourly_dip_swing/daily_lookback_grid.py
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
    print("[dlg] loading panels")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    keep = [c for c in panels["close"].columns if c not in CLIFF_SYMBOLS]
    close, trade, high = (panels["close"][keep], panels["trade"][keep],
                          panels["high"][keep])
    cross = breakout_cross(close, donchian_upper(high, 20)).fillna(False)
    dip = ((close / close.shift(5) - 1.0) < -0.05).fillna(False)

    rows, yearlies = {}, {}
    for lb, lb_name in [(21, "1m"), (63, "3m"), (126, "6m")]:
        rank = build_score_rank(close, lb)
        for entry_name, sig, use_ts20 in [("bo25", cross, False),
                                          ("dip25_ts20", dip, True)]:
            name = f"{entry_name}_{lb_name}"
            print(f"[dlg] simulating {name}")
            calls, counts, skipped = simulate(close, trade, sig, rank,
                                              cap=25, end=END,
                                              use_ts20=use_ts20)
            calls.to_csv(OUT_DIR / f"calls_daily_{name}.csv", index=False)
            pv = slot_curve(calls, close, 25, END)
            tail = pv.loc[pv.index >= TAIL_START]
            tail = tail / tail.iloc[0]
            rows[name] = {**cadence(calls, END), **group_stats(calls),
                          **curve_metrics(pv),
                          **{f"tail_{k}": v for k, v in curve_metrics(tail).items()},
                          "mean_active": round(float(counts.mean()), 1),
                          "pct_days_full": round(float((counts >= 25).mean()) * 100, 1),
                          "skipped": skipped}
            yearlies[name] = yearly(calls, pv)

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.to_csv(OUT_DIR / "summary_daily_lookback.csv")
    (OUT_DIR / "report_daily_lookback.json").write_text(
        json.dumps({"arms": rows, "yearly": yearlies}, indent=2, default=str))
    pd.set_option("display.width", 300)
    show = ["calls_per_year", "pct_weeks_with_call", "n_closed", "n_open",
            "win_rate_pct", "mean_pnl_pct", "median_pnl_pct", "p5_pnl_pct",
            "p95_pnl_pct", "median_hold_td", "cagr_pct", "sharpe",
            "max_dd_pct", "tail_cagr_pct", "tail_sharpe", "tail_max_dd_pct",
            "mean_active", "pct_days_full"]
    print("\n=== daily entries x momentum lookback, 2010-06 -> 2026-08-21 ===")
    print(df[show].to_string())


if __name__ == "__main__":
    main()
