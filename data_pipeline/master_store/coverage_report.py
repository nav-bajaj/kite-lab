"""Phase 1 gate: at every index event date from 2016, what fraction of the
index resolves to a symbol AND has a bhavcopy row that day?

Members on a date = rows of the reconstructed membership file active that day
+ leftover spells from resolution.csv active that day (those were dropped
from the membership file for want of a symbol). The denominator is the
index's fixed size, not the count we happen to hold, so an unresolved name
counts against coverage rather than vanishing.
"""
from __future__ import annotations

import os, sys
import pandas as pd
from data_pipeline.master_store.identity import Identity

from data_pipeline.master_store import ROOT as REPO, MASTER  # noqa: E402
RECON = f"{REPO}/tasks/index_reconstruction/data"
OUT = MASTER
SIZE = {"nse500": 500, "nifty50": 50, "nifty100": 100, "nifty250": 250}
FILES = {"nse500": "nse500_membership_reconstructed.csv", "nifty50": "nifty50_membership_reconstructed.csv",
         "nifty100": "nifty100_membership_reconstructed.csv", "nifty250": "nifty250_membership_reconstructed.csv"}


def main(start="2016-01-01"):
    eq = pd.read_parquet(f"{OUT}/bhavcopy_eq.parquet", columns=["date", "symbol"])
    traded = set(zip(eq["date"].dt.date, eq["symbol"]))
    days = sorted(set(eq["date"].dt.date))
    ident = Identity()
    print(f"identity: {ident.w['company'].nunique():,} companies over {len(ident.w):,} windows, {ident.n_edges} rename edges joined")

    def traded_on(sym: str, td, d) -> bool:
        sym = Identity.override(sym, d)
        if (td, sym) in traded:
            return True
        return any((td, s2) in traded for s2 in ident.symbols_on(sym, d))

    res = pd.read_csv(f"{OUT}/resolution.csv", parse_dates=["spell_from", "spell_to", "symbol_from", "symbol_to"])
    res = res[res["symbol"].notna() & res["method"].str.replace("+isin-set", "", regex=False).str.replace("+symbol-chain", "", regex=False).isin(["norm-exact", "token-exact", "manual-isin", "manual-symbol", "namechange-master"])]
    rows = []
    for idx, fn in FILES.items():
        m = pd.read_csv(f"{RECON}/{fn}", parse_dates=["effective_from", "effective_to"])
        m["effective_to"] = m["effective_to"].fillna(pd.Timestamp("2099-12-31"))
        r = res[res["index"] == idx]
        dates = sorted(set(m["effective_from"]) | set(r["spell_from"]))
        dates = [d for d in dates if d >= pd.Timestamp(start)]
        for d in dates:
            # nearest trading day on/after d
            td = next((x for x in days if x >= d.date()), None)
            if td is None:
                continue
            base = m[(m["effective_from"] <= d) & (m["effective_to"] > d)]
            extra = r[(r["spell_from"] <= d) & (r["spell_to"] > d)]
            members = {s: {s} for s in base["symbol"]}                  # file rows: keyed by symbol
            for name, g in extra.groupby("company_name"):               # leftovers: keyed by company
                members.setdefault(f"name:{name}", set()).update(g["symbol"])
            n_res = len(members)
            n_trd = sum(any(traded_on(s, td, d) for s in ss) for ss in members.values())
            rows.append((idx, d.date(), SIZE[idx], n_res, n_trd, round(100 * n_trd / SIZE[idx], 1)))
    df = pd.DataFrame(rows, columns=["index", "date", "size", "resolved", "traded_that_day", "coverage_pct"])
    df.to_csv(f"{OUT}/qa_coverage.csv", index=False)
    print(df.groupby("index").agg(dates=("date", "count"), min_cov=("coverage_pct", "min"),
                                  median_cov=("coverage_pct", "median"), last_cov=("coverage_pct", "last")).to_string())
    print()
    worst = df.sort_values("coverage_pct").groupby("index").head(3).sort_values(["index", "coverage_pct"])
    print(worst.to_string(index=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
