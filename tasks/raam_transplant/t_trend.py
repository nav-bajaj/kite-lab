"""T — trend as a soft, additive contributor to L6.

The paper scores a trend/breakout STATE and adds it to the ranking rather
than gating on it. L6's momentum (126d return / vol) already is a trend
measure, so the only incremental value a second trend term can add is a
DIFFERENT mechanic on a DIFFERENT clock: a breakout state that de-ranks a
still-high-momentum name that is quietly rolling over (broke below its
channel). That is exactly the failure L6-DIV showed in the choppy 2017-19
window, so that is where a win should show up if there is one.

final_score = L6_z + w * trend_signal

Two trend signals:
  DONCH  paper-style: +1 while in an uptrend (last event was a 42d-high
         breakout), -1 while in a downtrend (last was a 42d-low). Raw +/-1.
  DMA    "anything we've tried": distance of close above the 200-DMA,
         cross-sectionally z-scored (rewards established, extended uptrends).

Grid w on IS, read OOS (esp. OOS-A). Same L6 execution config, net 20bps.

Run:  python tasks/raam_transplant/t_trend.py
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
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6, build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from e1_l6div import _run_with_score, metrics, NSE500_UNIVERSE_CSV  # noqa: E402

WINDOWS = [
    ("IS", "2009-09-01", "2016-12-31"),
    ("OOS-A", "2017-01-01", "2019-12-31"),
    ("OOS-B", "2020-01-01", "2022-12-31"),
    ("OOS-C", "2023-01-01", "2026-07-20"),
]
DONCH_N = 42


def donchian_state(close: pd.DataFrame, n: int = DONCH_N) -> pd.DataFrame:
    roll_max = close.rolling(n).max()
    roll_min = close.rolling(n).min()
    state = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    state = state.mask(close >= roll_max, 1.0).mask(close <= roll_min, -1.0)
    return state.ffill().fillna(0.0)


def make_trend_score(l6_score, trend_panel, w, *, zscore_trend):
    def score_fn(d, **_):
        base = l6_score(d)
        if base is None or base.empty or w == 0.0:
            return base
        if d not in trend_panel.index:
            return base
        t = trend_panel.loc[d].reindex(base.index).astype(float).fillna(0.0)
        if zscore_trend and t.std(skipna=True) > 0:
            t = (t - t.mean()) / t.std()
        return base + w * t
    return score_fn


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"t_trend_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in nse500]

    l6_panels = build_momentum_panels(close_panel[cols],
                                      lookback_days=lookback_months_to_days(L6["lookback_months"]),
                                      skip_days=L6["skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=L6["vol_floor"], vol_power=L6["vol_power"],
                                   cross_sectional_zscore=L6["cross_sectional_zscore"])

    donch = donchian_state(close_panel[cols], DONCH_N)
    dma_dist = close_panel[cols] / sma_200[cols] - 1.0

    configs = [
        ("L6", l6_score),
        ("DONCH_w0.5", make_trend_score(l6_score, donch, 0.5, zscore_trend=False)),
        ("DONCH_w1.0", make_trend_score(l6_score, donch, 1.0, zscore_trend=False)),
        ("DONCH_w2.0", make_trend_score(l6_score, donch, 2.0, zscore_trend=False)),
        ("DMA_w0.25", make_trend_score(l6_score, dma_dist, 0.25, zscore_trend=True)),
        ("DMA_w0.5", make_trend_score(l6_score, dma_dist, 0.5, zscore_trend=True)),
        ("DMA_w1.0", make_trend_score(l6_score, dma_dist, 1.0, zscore_trend=True)),
    ]

    def run(sfn, s, e):
        r = _run_with_score(sfn, close_panel[cols], trade_panel[cols], calendar,
                            benchmark, l6_panels, sma_200[cols], atr_20[cols], s, e, dict(L6))
        return metrics(r, s, e) if r else {"error": "none"}

    rows = []
    base = {}
    for label, sfn in configs:
        rec = {"config": label}
        for wn, s, e in WINDOWS:
            m = run(sfn, s, e)
            rec[f"{wn}_cagr"] = m.get("cagr_pct")
            rec[f"{wn}_dd"] = m.get("max_dd_pct")
            rec[f"{wn}_calmar"] = m.get("calmar")
        rows.append(rec)
        if label == "L6":
            base = rec
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "trend_grid.csv", index=False)

    # deltas vs L6
    delta_rows = []
    for rec in rows:
        if rec["config"] == "L6":
            continue
        d = {"config": rec["config"]}
        for wn, _, _ in WINDOWS:
            d[f"{wn}_dCAGR"] = round((rec[f"{wn}_cagr"] or 0) - (base[f"{wn}_cagr"] or 0), 2)
            d[f"{wn}_dCalmar"] = round((rec[f"{wn}_calmar"] or 0) - (base[f"{wn}_calmar"] or 0), 3)
        oos = ["OOS-A", "OOS-B", "OOS-C"]
        d["OOS_mean_dCAGR"] = round(np.mean([d[f"{w}_dCAGR"] for w in oos]), 2)
        d["OOS_calmar_wins"] = int(sum(d[f"{w}_dCalmar"] > 0 for w in oos))
        d["OOS-A_dCAGR"] = d["OOS-A_dCAGR"]  # spotlight the choppy window
        delta_rows.append(d)
    ddf = pd.DataFrame(delta_rows)
    ddf.to_csv(out_dir / "trend_deltas.csv", index=False)
    (out_dir / "report.json").write_text(json.dumps({"grid": rows, "deltas": delta_rows}, indent=2, default=str))

    pd.set_option("display.width", 220, "display.max_columns", 40)
    print("\n" + "=" * 84)
    print("T — TREND-AUGMENTED L6")
    print("=" * 84)
    print("\nAbsolute (CAGR / MaxDD per window):")
    show = ["config"] + [f"{w}_cagr" for w, _, _ in WINDOWS] + [f"{w}_dd" for w, _, _ in WINDOWS]
    print(df[show].to_string(index=False))
    print("\nDeltas vs L6 (OOS-A is the choppy window trend should help most):")
    dshow = ["config", "OOS-A_dCAGR", "OOS-B_dCAGR", "OOS-C_dCAGR", "OOS_mean_dCAGR", "OOS_calmar_wins"]
    print(ddf[dshow].to_string(index=False))
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
