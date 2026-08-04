"""Dump weekly-resampled, rebased equity curves + metrics to JSON for the
findings artifact. Reuses the harness in us_in_2019_2025.py."""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from us_in_2019_2025 import (  # noqa: E402
    run_india, load_us, slice_result, WIN_START, WIN_END,
)


def weekly(pv: pd.Series) -> pd.Series:
    w = pv.resample("W-FRI").last().dropna()
    # keep exact window endpoints
    if pv.index[0] not in w.index:
        w = pd.concat([pv.iloc[[0]], w])
    if pv.index[-1] not in w.index:
        w = pd.concat([w, pv.iloc[[-1]]])
    return w / pv.iloc[0]


def main():
    india_results, nifty100 = run_india()
    us_results, spy = load_us()

    # persist Indian daily curves so we never re-run for this
    for label, res in india_results.items():
        slug = "l6_india" if "L6" in label else "om25_india"
        res["equity"].to_csv(HERE / f"equity_{slug}_daily.csv", index=False)

    series = {}
    dd = {}
    for label, res in {**india_results, **us_results}.items():
        sliced = slice_result(res["equity"], res["trades"], res["exits"])
        pv = sliced["equity"].set_index("date")["pv"]
        w = weekly(pv)
        series[label] = {
            "dates": [d.strftime("%Y-%m-%d") for d in w.index],
            "values": [round(v, 4) for v in w.values],
        }
        ddw = (w / w.cummax() - 1).round(4)
        dd[label] = [float(v) for v in ddw.values]

    for label, s in [("NIFTY 100", nifty100), ("SPY", spy)]:
        b = s.loc[WIN_START:WIN_END].dropna()
        w = weekly(b)
        series[label] = {
            "dates": [d.strftime("%Y-%m-%d") for d in w.index],
            "values": [round(v, 4) for v in w.values],
        }
        ddw = (w / w.cummax() - 1).round(4)
        dd[label] = [float(v) for v in ddw.values]

    summary = pd.read_csv(HERE / "summary_2019_2025.csv").to_dict("records")
    yearly = pd.read_csv(HERE / "yearly_2019_2025.csv", index_col=0)
    out = {
        "window": [str(WIN_START.date()), str(WIN_END.date())],
        "series": series,
        "drawdown": dd,
        "summary": summary,
        "yearly": {c: {int(y): float(v) for y, v in yearly[c].items()}
                   for c in yearly.columns},
    }
    (HERE / "artifact_data.json").write_text(json.dumps(out))
    print("wrote", HERE / "artifact_data.json")
    for k, v in series.items():
        print(f"  {k}: {len(v['dates'])} pts, final {v['values'][-1]:.3f}")


if __name__ == "__main__":
    main()
