"""Add after-tax weekly curves + yearly returns to artifact_data.json,
computed on DAILY equity curves (tax at the last trading day of each year,
25% of the year's net gain, losses carried forward), then weekly-resampled.
Benchmarks stay untaxed. Matches the table's daily-derived numbers."""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
ROOT = Path("/Users/navdeep/kite-lab")
TAX = 0.25
WIN_START, WIN_END = pd.Timestamp("2019-01-01"), pd.Timestamp("2025-12-31")

DAILY = {
    "Core Momentum (L6 v2) — India": HERE / "equity_l6_india_daily.csv",
    "Quality Momentum (OM25 v3) — India": HERE / "equity_om25_india_daily.csv",
    "Core Momentum (L6 v2) — US": ROOT / "experiments/us_strategies_2017/l6_v2/equity.csv",
    "Quality Momentum (OM25 v3) — US": ROOT / "experiments/us_strategies_2017/om25_v3/equity.csv",
}

data = json.loads((HERE / "artifact_data.json").read_text())


def weekly(pv: pd.Series) -> pd.Series:
    w = pv.resample("W-FRI").last().dropna()
    if pv.index[0] not in w.index:
        w = pd.concat([pv.iloc[[0]], w])
    if pv.index[-1] not in w.index:
        w = pd.concat([w, pv.iloc[[-1]]])
    return w


series_tax = {}
yearly_tax = {}
for key, path in DAILY.items():
    eq = pd.read_csv(path, parse_dates=["date"])
    pv = eq.set_index("date")["pv"].loc[WIN_START:WIN_END]
    pv = pv / pv.iloc[0]

    cap, base, carry = 1.0, 1.0, 0.0
    out = [cap]
    yr_net = {}
    years = pv.index.year
    for i in range(1, len(pv)):
        cap *= pv.iloc[i] / pv.iloc[i - 1]
        last_of_year = i + 1 == len(pv) or years[i + 1] > years[i]
        if last_of_year:
            gain = cap - base
            if gain > 0:
                taxable = max(0.0, gain - carry)
                carry = max(0.0, carry - gain)
                cap -= TAX * taxable
            else:
                carry += -gain
            yr_net[int(years[i])] = round((cap / base - 1) * 100, 2)
            base = cap
        out.append(cap)
    post = pd.Series(out, index=pv.index)
    w = weekly(post)
    # align to the shared weekly date grid of the pre-tax series
    grid = pd.to_datetime(data["series"][key]["dates"])
    aligned = post.reindex(grid, method="ffill")
    series_tax[key] = [round(v, 4) for v in aligned.values]
    yearly_tax[key] = yr_net
    n = len(yr_net)
    print(f"{key}: final {post.iloc[-1]:.2f}x  CAGR {(post.iloc[-1]**(1/n)-1)*100:.1f}%")

data["series_tax"] = series_tax
data["yearly_tax"] = yearly_tax
(HERE / "artifact_data.json").write_text(json.dumps(data))
print("updated artifact_data.json")
