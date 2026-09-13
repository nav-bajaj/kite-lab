"""§1 — build data/daily.parquet. One pass, long format, concat once."""
from __future__ import annotations

import sys
import time

import pandas as pd

sys.path.insert(0, "tasks/trigger_calls_2026/lib")
from daily_features import daily_features, eligible_universe  # noqa: E402

OUT = "tasks/trigger_calls_2026/data/daily.parquet"


def main() -> None:
    t0 = time.time()
    u = eligible_universe()
    allow = {s: set(g) for s, g in u.groupby("symbol")["date"]}
    frames = []
    for i, sym in enumerate(sorted(allow)):
        d = daily_features(sym, allow[sym])
        if d is not None:
            frames.append(d)
        if i % 250 == 0:
            print(f"{i}/{len(allow)} {time.time()-t0:.0f}s", flush=True)
    out = pd.concat(frames, ignore_index=True)
    out = out.merge(u, on=["date", "symbol"], how="left")
    le = out["state"].isin(["LEADING", "EXTENDED"])
    out["rk"] = (out[le].groupby("date")["above_low"]
                 .rank(ascending=False, method="first"))
    for c in ("close", "s50", "s100", "s150", "s200", "s200_21", "hi52",
              "lo52", "above_low", "adv", "rk"):
        out[c] = out[c].astype("float32")
    out.to_parquet(OUT, index=False)
    print(f"rows={len(out)} syms={out.symbol.nunique()} "
          f"dates={out.date.nunique()} {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
