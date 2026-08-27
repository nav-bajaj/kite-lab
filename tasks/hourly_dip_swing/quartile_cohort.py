"""Addendum to quartile_compare.py: the entry cohort, without the portfolio.

Portfolio arms mix the sleeve effect with cap/slot mechanics (Q3 sees far
more signals, so the cap bites differently). This measures the raw dip
signal: forward return from the next day's fill, by momentum-sleeve band,
against the same-day universe baseline -- the house validity-protocol view.

Run:  .venv/bin/python tasks/hourly_dip_swing/quartile_cohort.py
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

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols,
)
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402
from tasks.dip_vs_breakout_calls.experiment import CLIFF_SYMBOLS, START  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
END = pd.Timestamp("2026-08-21")
HORIZONS = [20, 60]
BANDS = {"q1": (0.75, 1.01), "q2": (0.50, 0.75), "q3": (0.25, 0.50)}


def main():
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    keep = [c for c in panels["close"].columns if c not in CLIFF_SYMBOLS]
    close = panels["close"][keep]
    win = (close.index >= START) & (close.index <= END)

    dip = ((close / close.shift(5) - 1.0) < -0.05).fillna(False)
    rank = build_score_rank(close, 126)
    out = {}
    for h in HORIZONS:
        fwd = close.shift(-h) / close - 1.0
        base = fwd.mean(axis=1)                       # equal-weight same-day universe
        excess = fwd.sub(base, axis=0)
        for name, (lo, hi) in BANDS.items():
            m = dip & (rank >= lo) & (rank < hi) & pd.Series(win, index=close.index).to_numpy()[:, None]
            e = excess.where(m).to_numpy()
            a = fwd.where(m).to_numpy()
            e, a = e[~np.isnan(e)], a[~np.isnan(a)]
            se = e.std(ddof=1) / np.sqrt(len(e)) if len(e) > 1 else np.nan
            out[f"{name}_{h}d"] = {
                "n": int(len(e)),
                "mean_excess_pp": round(float(e.mean()) * 100, 2),
                "t_stat": round(float(e.mean() / se), 2) if se and se > 0 else None,
                "median_excess_pp": round(float(np.median(e)) * 100, 2),
                "mean_abs_pp": round(float(a.mean()) * 100, 2),
                "win_vs_universe_pct": round(float((e > 0).mean()) * 100, 1),
            }
    df = pd.DataFrame(out).T
    df.index.name = "cohort"
    df.to_csv(OUT_DIR / "summary_quartile_cohort.csv")
    (OUT_DIR / "report_quartile_cohort.json").write_text(
        json.dumps(out, indent=2, default=str))
    pd.set_option("display.width", 240)
    print("\n=== dip-signal forward return vs same-day universe, by sleeve ===")
    print(df.to_string())


if __name__ == "__main__":
    main()
