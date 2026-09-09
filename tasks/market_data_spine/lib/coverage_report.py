"""Phase 1 gate: at every index event date from 2016, what fraction of the
index resolves to a symbol AND has a bhavcopy row that day?

Members on a date = rows of the reconstructed membership file active that day
+ leftover spells from resolution.csv active that day (those were dropped
from the membership file for want of a symbol). The denominator is the
index's fixed size, not the count we happen to hold, so an unresolved name
counts against coverage rather than vanishing.
"""
from __future__ import annotations

import sys
import pandas as pd

REPO = "/Users/navdeep/kite-lab"
RECON = f"{REPO}/tasks/index_reconstruction/data"
OUT = f"{REPO}/data/master"
SIZE = {"nse500": 500, "nifty50": 50, "nifty100": 100, "nifty250": 250}
FILES = {"nse500": "nse500_membership_reconstructed.csv", "nifty50": "nifty50_membership_reconstructed.csv",
         "nifty100": "nifty100_membership_reconstructed.csv", "nifty250": "nifty250_membership_reconstructed.csv"}


def main(start="2016-01-01"):
    eq = pd.read_parquet(f"{OUT}/bhavcopy_eq.parquet", columns=["date", "symbol"])
    traded = set(zip(eq["date"].dt.date, eq["symbol"]))
    days = sorted(set(eq["date"].dt.date))
    # symbol -> ISINs it ever carried; ISIN -> (symbol, window) so a member listed
    # under today's ticker is found under the ticker it traded as on the day
    win = pd.read_csv(f"{OUT}/symbol_master.csv", parse_dates=["first_seen", "last_seen"])
    isins_of = win.groupby("symbol")["isin"].agg(set).to_dict()
    wins_of = {k: list(zip(g["symbol"], g["first_seen"].dt.date, g["last_seen"].dt.date))
               for k, g in win.groupby("isin")}

    def traded_on(sym: str, td) -> bool:
        if (td, sym) in traded:
            return True
        # two hops: today's ticker -> its ISINs -> tickers under them -> THEIR
        # ISINs (a face-value split changes the ISIN, not the symbol)
        seen_isin, seen_sym, frontier = set(), {sym}, {sym}
        for _ in range(2):
            new = set()
            for s1 in frontier:
                for isin in isins_of.get(s1, ()):
                    if isin in seen_isin or isin.startswith("SYM:"):
                        continue
                    seen_isin.add(isin)
                    for s2, a, b in wins_of.get(isin, ()):
                        if a <= td <= b and (td, s2) in traded:
                            return True
                        if s2 not in seen_sym:
                            seen_sym.add(s2); new.add(s2)
            frontier = new
        return False
    res = pd.read_csv(f"{OUT}/resolution.csv", parse_dates=["spell_from", "spell_to", "symbol_from", "symbol_to"])
    res = res[res["symbol"].notna() & res["method"].str.replace("+isin-set", "", regex=False).isin(["norm-exact", "token-exact", "manual-isin", "manual-symbol", "namechange-master"])]
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
            n_trd = sum(any(traded_on(s, td) for s in ss) for ss in members.values())
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
