"""Cheap first cut on the parked momentum-rebuild idea (RESULTS.md, Addendum 8).

Signal under test: a name dips (-5% over 5 days) while sitting in the
LOWER half of the momentum ranking, then climbs back through a threshold
within N trading days. Buy the confirmation of the rebuild, not the dip.

Cohort test only -- no portfolio, no cap, no slots. If there is no
forward excess at 20/60 days the idea stops here, per the protocol note.

Controls run alongside so the number means something:
  q1_dip     the published feed's entry cohort (should show +1.02pp @20d)
  q3_dip     the third-quartile dip (should show ~0)
  cross_only the rank crossing WITHOUT a prior dip -- isolates whether any
             edge belongs to the rebuild or just to momentum acceleration
  rebuild_*  the idea itself, over threshold x window

Excess is vs the same-day equal-weight universe. Two t-stats are
reported: naive (every signal independent, overstated -- signals cluster
in time) and a date-clustered t on the daily mean excess, which is the
one to trust.

Run:  .venv/bin/python tasks/hourly_dip_swing/rebuild_cohort.py
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


def cohort_stats(mask, fwd, excess):
    e = excess.where(mask)
    a = fwd.where(mask)
    flat_e = e.to_numpy()[~np.isnan(e.to_numpy())]
    flat_a = a.to_numpy()[~np.isnan(a.to_numpy())]
    if len(flat_e) < 30:
        return {"n": int(len(flat_e))}
    se = flat_e.std(ddof=1) / np.sqrt(len(flat_e))
    daily = e.mean(axis=1).dropna()          # one observation per date
    se_d = daily.std(ddof=1) / np.sqrt(len(daily))
    return {
        "n": int(len(flat_e)),
        "n_dates": int(len(daily)),
        "mean_excess_pp": round(float(flat_e.mean()) * 100, 2),
        "t_naive": round(float(flat_e.mean() / se), 2) if se > 0 else None,
        "t_clustered": round(float(daily.mean() / se_d), 2) if se_d > 0 else None,
        "median_excess_pp": round(float(np.median(flat_e)) * 100, 2),
        "mean_abs_pp": round(float(flat_a.mean()) * 100, 2),
        "win_vs_universe_pct": round(float((flat_e > 0).mean()) * 100, 1),
    }


def main():
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    keep = [c for c in panels["close"].columns if c not in CLIFF_SYMBOLS]
    close = panels["close"][keep]
    in_win = pd.Series((close.index >= START) & (close.index <= END),
                       index=close.index)
    w = in_win.to_numpy()[:, None]

    dip = ((close / close.shift(5) - 1.0) < -0.05).fillna(False)
    rank = build_score_rank(close, 126)

    # a dip taken while in the lower half of the ranking
    dip_low = dip & (rank < 0.50) & (rank >= 0.25)

    cohorts = {}
    cohorts["q1_dip"] = dip & (rank >= 0.75)
    cohorts["q3_dip"] = dip_low

    for thr in (0.65, 0.75):
        cross = (rank >= thr) & (rank.shift(1) < thr)
        cohorts[f"cross_only_{int(thr*100)}"] = cross
        for win in (20, 40):
            recent_dip = (dip_low.shift(1).rolling(win, min_periods=1)
                          .max().fillna(0) > 0)
            cohorts[f"rebuild_t{int(thr*100)}_n{win}"] = cross & recent_dip

    out = {}
    for h in HORIZONS:
        fwd = close.shift(-h) / close - 1.0
        base = fwd.mean(axis=1)
        excess = fwd.sub(base, axis=0)
        for name, m in cohorts.items():
            out[f"{name}_{h}d"] = cohort_stats(m & w, fwd, excess)

    df = pd.DataFrame(out).T
    df.index.name = "cohort"
    df.to_csv(OUT_DIR / "summary_rebuild_cohort.csv")
    (OUT_DIR / "report_rebuild_cohort.json").write_text(
        json.dumps(out, indent=2, default=str))
    pd.set_option("display.width", 260)
    print("\n=== momentum-rebuild cohort: forward excess vs same-day universe ===")
    print(df.to_string())


if __name__ == "__main__":
    main()
