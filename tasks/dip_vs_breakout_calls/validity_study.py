"""Validity-protocol study for the dip-entry momentum feed.

Replicates the tasks/insight_engine/pattern_validity_study.py
methodology (stride-21 date sampling from 2012-01-01 to last-180d,
top-25 firings per date, unconditional same-date NSE-500 baseline,
horizons 5/20/60/120d) over the dip_vs_breakout_calls study panel, and
adds the protocol's check-4 (sign consistency across 5/20/60d) and
check-6 (persistence across sample halves) explicitly.

Detectors, both gated to top-quartile 126d momentum score and ranked
by that score (identical to the feed's slot priority):
  dip_momentum      5-day return < -5%   (a state; persists over days)
  breakout_momentum fresh close above prior 20d high (an event)

Universe: NSE 500 minus the 33 cliff-artifact symbols (both fires AND
baseline, so the comparison stays internally consistent).

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/validity_study.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols, donchian_upper, breakout_cross,
)
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402
from tasks.dip_vs_breakout_calls.experiment import CLIFF_SYMBOLS  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
PV_DIR = ROOT / "tasks/insight_engine/PATTERN_VALIDITY"
HORIZONS = [5, 20, 60, 120]
STRIDE = 21
STUDY_START = pd.Timestamp("2012-01-01")
END_BUFFER_DAYS = 180
TOP_N = 25
QUARTILE = 0.75


def horizon_stats(fires, base):
    fires, base = np.array(fires) * 100, np.array(base) * 100
    return dict(
        n_fires=len(fires),
        mean=round(float(fires.mean()), 2),
        median=round(float(np.median(fires)), 2),
        baseline_mean=round(float(base.mean()), 2),
        excess_pp=round(float(fires.mean() - base.mean()), 2),
        pct_pos=round(float((fires > 0).mean()) * 100, 1),
        base_pct_pos=round(float((base > 0).mean()) * 100, 1),
        lift_pp=round(float((fires > 0).mean() - (base > 0).mean()) * 100, 1),
    )


def main():
    print("[validity] loading panel")
    syms = [s for s in load_universe_symbols() if s not in CLIFF_SYMBOLS]
    panels = load_ohlc_panels(symbols=syms)
    close, high = panels["close"], panels["high"]
    rank = build_score_rank(close, 126)
    ret5 = close / close.shift(5) - 1.0
    dip_sig = ((ret5 < -0.05) & (rank >= QUARTILE)).fillna(False)
    bo_sig = (breakout_cross(close, donchian_upper(high, 20)).fillna(False)
              & (rank >= QUARTILE))

    end_cap = close.index.max() - pd.Timedelta(days=END_BUFFER_DAYS)
    dates = close.index[(close.index >= STUDY_START) & (close.index <= end_cap)]
    dates = list(dates[::STRIDE])
    print(f"[validity] {len(dates)} sample dates "
          f"{dates[0].date()} -> {dates[-1].date()}")

    idx_of = {d: i for i, d in enumerate(close.index)}
    cl_v = close.to_numpy()

    detectors = {"dip_momentum": dip_sig, "breakout_momentum": bo_sig}
    results = {}
    for name, sig in detectors.items():
        per_h = {h: {"fire": [], "base": [], "fire_dates": [], } for h in HORIZONS}
        n_dates_with_fire = 0
        for d in dates:
            i = idx_of[d]
            row = sig.loc[d]
            fired = row.index[row.to_numpy()]
            if len(fired) == 0:
                continue
            rk = rank.loc[d, fired].dropna().sort_values(ascending=False)
            picks = list(rk.index[:TOP_N])
            n_dates_with_fire += 1
            for h in HORIZONS:
                if i + h >= len(close.index):
                    continue
                fwd = cl_v[i + h] / cl_v[i] - 1.0
                fwd_s = pd.Series(fwd, index=close.columns)
                f = fwd_s.reindex(picks).dropna()
                b = fwd_s.dropna()
                per_h[h]["fire"].extend(f.values.tolist())
                per_h[h]["base"].extend(b.values.tolist())
                per_h[h]["fire_dates"].extend([d] * len(f))
        stats = {h: horizon_stats(v["fire"], v["base"])
                 for h, v in per_h.items() if v["fire"]}

        # check 6: persistence across sample halves at 20d
        f20 = pd.DataFrame({"d": per_h[20]["fire_dates"],
                            "r": per_h[20]["fire"]})
        b20 = pd.DataFrame({"d": [d for d in dates for _ in range(1)],
                            })
        mid = dates[len(dates) // 2]
        halves = {}
        for lab, mask_f in (("H1", f20.d < mid), ("H2", f20.d >= mid)):
            fires = f20[mask_f]
            # matched baseline: recompute over same date subset
            bb, ff = [], []
            for d in (set(fires.d)):
                i = idx_of[d]
                if i + 20 >= len(close.index):
                    continue
                fwd = cl_v[i + 20] / cl_v[i] - 1.0
                bb.extend(pd.Series(fwd, index=close.columns).dropna().values.tolist())
            halves[lab] = dict(
                n=len(fires),
                excess_pp=round(float(fires.r.mean() * 100 -
                                      np.mean(bb) * 100), 2) if bb else None)
        results[name] = dict(stats=stats, halves=halves,
                             n_dates_with_fire=n_dates_with_fire)

    # ---- report ----
    lines = ["# Pattern validity study — dip_momentum (vs breakout_momentum control)",
             "",
             f"- Methodology: replica of tasks/insight_engine/pattern_validity_study.py",
             f"- Sample: {len(dates)} dates, stride {STRIDE}, "
             f"{dates[0].date()} -> {dates[-1].date()}; top-{TOP_N} by momentum "
             "score per date",
             "- Universe/baseline: NSE 500 minus 33 cliff-artifact symbols "
             "(tasks/dip_vs_breakout_calls/PLAN.md); baseline = all universe "
             "stocks, same dates",
             ""]
    for name, r in results.items():
        lines += [f"## {name}", "",
                  "| Horizon | N fires | Mean fwd % | Median | Baseline mean % | Excess (pp) | % pos | Base % pos | Lift (pp) |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for h in HORIZONS:
            if h not in r["stats"]:
                continue
            s = r["stats"][h]
            lines.append(f"| {h}d | {s['n_fires']} | {s['mean']:+.2f} | "
                         f"{s['median']:+.2f} | {s['baseline_mean']:+.2f} | "
                         f"{s['excess_pp']:+.2f} | {s['pct_pos']:.0f}% | "
                         f"{s['base_pct_pos']:.0f}% | {s['lift_pp']:+.1f} |")
        h1, h2 = r["halves"]["H1"], r["halves"]["H2"]
        lines += ["",
                  f"- Persistence (20d excess by sample half): "
                  f"H1 {h1['excess_pp']:+.2f}pp (n={h1['n']}), "
                  f"H2 {h2['excess_pp']:+.2f}pp (n={h2['n']})",
                  f"- Dates with >= 1 fire: {r['n_dates_with_fire']}/{len(dates)}",
                  ""]
        s20 = r["stats"].get(20)
        signs = [np.sign(r["stats"][h]["excess_pp"])
                 for h in (5, 20, 60) if h in r["stats"]]
        consistent = len(set(signs)) == 1
        if s20:
            checks = {
                "1 sample n>=100": s20["n_fires"] >= 100,
                "2 excess >= +1.0pp @20d": s20["excess_pp"] >= 1.0,
                "3 direction lift > 0 @20d": s20["lift_pp"] > 0,
                "4 sign consistency 5/20/60d": consistent,
                "6 persistence (both halves same sign)": (
                    h1["excess_pp"] is not None and h2["excess_pp"] is not None
                    and np.sign(h1["excess_pp"]) == np.sign(h2["excess_pp"])
                    and h1["excess_pp"] != 0),
            }
            for c, ok in checks.items():
                lines.append(f"- check {c}: {'PASS' if ok else 'FAIL'}")
            if all(checks.values()):
                tier = "VALIDATED (all checks pass; check 5 carries the standing survivorship caveat)"
            elif s20["lift_pp"] > 0 and s20["excess_pp"] >= 0.3:
                tier = "NAMES-ONLY (lift positive, excess modest)"
            else:
                tier = "NOT SURFACED"
            lines += ["", f"**Tier: {tier}**", ""]
    report = "\n".join(lines)
    (OUT_DIR / "VALIDITY.md").write_text(report)
    PV_DIR.mkdir(exist_ok=True)
    (PV_DIR / "dip_momentum_entry.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
