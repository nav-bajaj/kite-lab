"""Dip vs breakout call feeds — US equities generalisation test.

Runs the exact engine from ../experiment.py (imported, not copied) on the
US panel (us_equities_data/, SP500 union Nasdaq100 universe, EODHD
split/dividend-adjusted). No parameters retuned: 126d momentum score,
top-quartile filter, exit at momentum rank < 0.35, caps 25/50, 20% trail,
20bps slippage. Same window start (2010-06-01) and tail split (2023-07-01)
as the India study; END is the US data end (2026-07-23).

Differences vs the India run, by design:
  - No cliff-symbol exclusion: the US feed is supplier-adjusted so one-day
    cliffs are real crashes, not corporate-action artifacts. A scan is
    printed for the record.
  - No regression arm: there is no published US number for this engine.
    The panel loader is shared with the l6_us_tune / us_strategies runs.

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/us_equities/experiment_us.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tasks.dip_vs_breakout_calls.experiment as exp  # noqa: E402
from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, donchian_upper, breakout_cross,
)
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
PRICES_DIR = ROOT / "us_equities_data"
UNIVERSE_CSV = ROOT / "data/static/us_equities_universe.csv"
END = pd.Timestamp("2026-07-23")


def main():
    print("[us] loading panels")
    syms = sorted(pd.read_csv(UNIVERSE_CSV)["Symbol"].dropna().astype(str).unique())
    panels = load_ohlc_panels(prices_dir=PRICES_DIR, symbols=syms)
    close, trade, high = panels["close"], panels["trade"], panels["high"]
    print(f"  panel {close.shape}, {close.index.min().date()} .. {close.index.max().date()}")

    rets = close.pct_change()
    down = (rets < -0.30).sum().sum()
    up = (rets > 0.50).sum().sum()
    worst = rets.min().sort_values().head(10)
    print(f"[us] cliff scan: {int(down)} one-day drops < -30%, {int(up)} gains > +50%")
    print(worst.round(3).to_string())

    rank = build_score_rank(close, 126)
    cross = breakout_cross(close, donchian_upper(high, 20)).fillna(False)
    ret5 = close / close.shift(5) - 1.0
    dip = (ret5 < -0.05).fillna(False)
    s200 = close.rolling(200).mean()
    dip_trend = (dip & (close > s200)).fillna(False)

    arms = [
        ("bo25",        cross,     25, False),
        ("bo25_ts20",   cross,     25, True),
        ("dip25",       dip,       25, False),
        ("dip25_ts20",  dip,       25, True),
        ("dip25_trend", dip_trend, 25, False),
        ("bo50",        cross,     50, False),
        ("dip50_ts20",  dip,       50, True),
    ]
    rows, yearlies = {}, {}
    for name, sig, cap, ts in arms:
        print(f"[us] simulating {name}")
        calls, counts, skipped = exp.simulate(close, trade, sig, rank,
                                              cap=cap, end=END, use_ts20=ts)
        calls.to_csv(OUT_DIR / f"calls_{name}.csv", index=False)
        pv = exp.slot_curve(calls, close, cap, END)
        tail = pv.loc[pv.index >= exp.TAIL_START]
        tail = tail / tail.iloc[0]
        rows[name] = {**exp.cadence(calls, END), **exp.group_stats(calls),
                      **exp.curve_metrics(pv),
                      **{f"tail_{k}": v for k, v in exp.curve_metrics(tail).items()},
                      "mean_active": round(float(counts.mean()), 1),
                      "pct_days_full": round(float((counts >= cap).mean()) * 100, 1),
                      "skipped": skipped}
        yearlies[name] = exp.yearly(calls, pv)

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.to_csv(OUT_DIR / "summary_us.csv")
    (OUT_DIR / "report_us.json").write_text(json.dumps(
        {"cliff_scan": {"n_drops_lt_-30pct": int(down), "n_gains_gt_50pct": int(up)},
         "arms": rows, "yearly": yearlies}, indent=2))
    pd.set_option("display.width", 300)
    show = ["calls_per_year", "pct_weeks_with_call", "n_closed", "n_open",
            "win_rate_pct", "mean_pnl_pct", "median_pnl_pct", "p5_pnl_pct",
            "p95_pnl_pct", "median_hold_td", "cagr_pct", "sharpe",
            "max_dd_pct", "tail_cagr_pct", "tail_sharpe", "tail_max_dd_pct",
            "mean_active", "pct_days_full"]
    print("\n=== dip vs breakout, US equities (xr35) ===")
    print(df[show].to_string())


if __name__ == "__main__":
    main()
