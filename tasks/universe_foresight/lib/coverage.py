"""How optimistic is b4? It ranks turnover inside the price panel, and the panel
holds ever-members of the four NSE indices. Names that never made any index are
therefore unselectable -- and those are disproportionately the ones that did not
go on to work. This measures the hole: at each monthly review, what share of the
true top-N by turnover across ALL listed EQ names is missing from the panel."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TASK / "lib"))
import buckets as B  # noqa: E402


def measure(top_n: int, window: int = 63) -> pd.DataFrame:
    panel = {p.name[:-8] for p in B.PANEL.glob("*_day.csv")}
    traded = {}
    for f in sorted(B.PANEL.glob("*_day.csv")):
        d = pd.read_csv(f, usecols=["date", "traded_as"], parse_dates=["date"])
        for s in d["traded_as"].dropna().unique():
            traded[s] = f.name[:-8]
    bc = pd.read_parquet(B.MASTER / "bhavcopy_eq.parquet", columns=["date", "symbol", "series", "close", "volume"])
    bc = bc[bc["series"] == "EQ"].copy()
    bc["tv"] = bc["close"] * bc["volume"]
    wide = bc.pivot_table(index="date", columns="symbol", values="tv", aggfunc="sum").sort_index()
    med = wide.rolling(window, min_periods=window // 2).median()
    idx = med.index
    months = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).first()
    rows = []
    for d in months:
        top = med.loc[d].nlargest(top_n)
        inside = sum(1 for s in top.index if traded.get(s, s) in panel)
        rows.append(dict(date=d, top_n=top_n, in_panel=inside, missing=top_n - inside,
                         missing_pct=100 * (top_n - inside) / top_n))
    return pd.DataFrame(rows).set_index("date")


if __name__ == "__main__":
    for n in (250, 500):
        df = measure(n)
        df.to_csv(TASK / f"report/coverage_top{n}.csv")
        yr = df.groupby(df.index.year)["missing_pct"].mean()
        print(f"\ntop-{n} by turnover, share absent from the price panel (annual mean %)")
        print("  " + "  ".join(f"{y}:{v:4.0f}" for y, v in yr.items()), flush=True)
        print(f"  span mean {df.missing_pct.mean():.0f}%  | 2016+ mean {df[df.index >= '2016'].missing_pct.mean():.0f}%", flush=True)
