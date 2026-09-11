"""Phase 3: the raw price layer — one bhavcopy series per company, keyed by
its canonical symbol, from the daily archive already fetched.

For every target (the Kite target list, which is every index member and
resolved leftover mapped to the ticker its company trades under today) the
company's trading windows come from the identity layer, so INFY's file
carries the INFOSYSTCH years and COLPAL's carries COLGATE's. Rows are the
bhavcopy's own OHLC, LAST, PREVCLOSE and volume — what traded, unadjusted.
EQ series preferred, then BE/BZ on days EQ did not print.

`delisted_on` in the manifest is the company's last traded date when that
is more than 20 sessions before the archive end (D-9: exit at last traded
price). Writes data/master/prices/bhavcopy/<SYMBOL>.csv and a manifest.
"""
from __future__ import annotations

import glob, hashlib, json, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from identity import Identity

REPO = "/Users/navdeep/kite-lab"
MASTER = f"{REPO}/data/master"
OUT = f"{MASTER}/prices/bhavcopy"
MANIFEST = f"{MASTER}/prices/bhavcopy_manifest.json"
# Optional, additive: extra canonical symbols to export beyond the index-member
# target list. Absent -> behaviour is exactly as before. Written by
# tasks/breakout_calls_2026, which needs every name that ever cleared its
# liquidity floor, not only index members.
EXTRA_TARGETS = f"{MASTER}/extra_targets.csv"


def main():
    os.makedirs(OUT, exist_ok=True)
    eq = pd.read_parquet(f"{MASTER}/bhavcopy_eq.parquet")
    eq["pri"] = eq["series"].map({"EQ": 0, "BE": 1, "BZ": 2}).fillna(3)
    end = eq["date"].max()
    sessions = sorted(eq["date"].unique())
    cutoff = pd.Timestamp(sessions[-21])
    ident = Identity()
    targets = pd.read_csv(f"{MASTER}/kite_targets.csv")
    keys = {s for v in targets["symbol"] for s in str(v).split("|")}
    for f in glob.glob(f"{MASTER}/membership/*.csv"):
        keys |= set(pd.read_csv(f)["symbol"])
    if os.path.exists(EXTRA_TARGETS):
        extra = set(pd.read_csv(EXTRA_TARGETS)["symbol"])
        print(f"  extra_targets.csv: +{len(extra - keys)} symbols beyond the index-member list")
        keys |= extra
    keys = sorted(keys)
    by_symbol = {s: g for s, g in eq.groupby("symbol")}
    manifest, n_ok, n_empty, n_delisted = {}, 0, 0, 0
    for i, key in enumerate(keys, 1):
        # every (symbol, window) of the company, or just the symbol if unknown to the master
        comps = ident.companies(key)
        wins = pd.concat([ident.by_company[c] for c in comps]) if comps else pd.DataFrame(
            {"symbol": [key], "first_seen": [pd.Timestamp("1900-01-01")], "last_seen": [end]})
        frames = []
        for w in wins.itertuples():
            g = by_symbol.get(w.symbol)
            if g is None:
                continue
            frames.append(g[(g["date"] >= w.first_seen) & (g["date"] <= w.last_seen)].assign(traded_as=w.symbol))
        if not frames:
            n_empty += 1; manifest[key] = {"error": "no bhavcopy rows"}; continue
        df = pd.concat(frames).sort_values(["date", "pri"]).drop_duplicates("date", keep="first")
        df = df[["date", "open", "high", "low", "close", "last", "prevclose", "volume", "series", "isin", "traded_as"]].sort_values("date")
        df.to_csv(f"{OUT}/{key}.csv", index=False)
        last = df["date"].max()
        entry = {"first": str(df["date"].min().date()), "last": str(last.date()), "rows": int(len(df)),
                 "traded_as": sorted(set(df["traded_as"])), "basis": "bhavcopy-raw",
                 "sha256": hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()}
        if last < cutoff:
            entry["delisted_on"] = str(last.date()); n_delisted += 1
        manifest[key] = entry; n_ok += 1
        if i % 200 == 0:
            print(f"  {i}/{len(keys)}", flush=True)
    json.dump(manifest, open(MANIFEST, "w"), indent=1)
    print(f"written {n_ok}, no rows {n_empty}, flagged delisted {n_delisted}; archive end {end.date()}")


if __name__ == "__main__":
    main()
