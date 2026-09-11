"""Phase 2: point-in-time membership files for the four indices, in the
loader's schema, keyed by the symbol each company's price file uses.

Sources: the reconstruction's membership files (already exact against
today's list and the 2022 factsheets) plus the leftover spells Phase 1
resolved. Each row's symbol is (1) redirected by LINE_OVERRIDES where the
reconstruction attached a historical member to the wrong listed line, the
spell split at the cutover, then (2) mapped to the company's canonical
symbol — the ticker it trades under most recently, which is also the key
the Kite pull and the bhavcopy series use. Contiguous spells under one key
are merged.

Writes data/master/membership/<index>.csv. Production data/static/ is not
touched (D-8).
"""
from __future__ import annotations

import os, sys
import pandas as pd

from data_pipeline.master_store.identity import Identity, LINE_OVERRIDES

from data_pipeline.master_store import ROOT as REPO, MASTER  # noqa: E402
RECON = f"{REPO}/tasks/index_reconstruction/data"
MASTER = MASTER
OUT = f"{MASTER}/membership"
SIZE = {"nse500": 500, "nifty50": 50, "nifty100": 100, "nifty250": 250}
ACCEPT = {"norm-exact", "token-exact", "manual-isin", "manual-symbol", "namechange-master"}
FAR = pd.Timestamp("2099-12-31")


def spells_for(idx: str) -> pd.DataFrame:
    m = pd.read_csv(f"{RECON}/{idx}_membership_reconstructed.csv", parse_dates=["effective_from", "effective_to"])
    m["effective_to"] = m["effective_to"].fillna(FAR)
    m["note"] = m["note"].fillna("").astype(str)
    res = pd.read_csv(f"{MASTER}/resolution.csv", parse_dates=["spell_from", "spell_to", "symbol_from", "symbol_to"])
    res = res[(res["index"] == idx) & res["symbol"].notna()]
    res = res[res["method"].str.replace("+isin-set", "", regex=False).str.replace("+symbol-chain", "", regex=False).isin(ACCEPT)]
    # a leftover may resolve to several symbols over the spell; one row per symbol window
    extra = pd.DataFrame({
        "symbol": res["symbol"],
        "effective_from": res["symbol_from"].fillna(res["spell_from"]),
        "effective_to": res["symbol_to"].fillna(res["spell_to"]),
        "note": res["company_name"] + " [" + res["method"] + "]",
    })
    return pd.concat([m[["symbol", "effective_from", "effective_to", "note"]], extra], ignore_index=True)


def apply_overrides(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in df.itertuples(index=False):
        cuts = LINE_OVERRIDES.get(r.symbol, [])
        if not cuts:
            rows.append(r); continue
        a, b = r.effective_from, r.effective_to
        for before, hist in cuts:
            cut = pd.Timestamp(before)
            if a < cut:
                rows.append((hist, a, min(b, cut), f"{r.note} [line-override<{before}]"))
                a = cut
        if a < b:
            rows.append((r.symbol, a, b, r.note))
    return pd.DataFrame(rows, columns=["symbol", "effective_from", "effective_to", "note"])


def merge_spells(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["symbol", "effective_from"]).reset_index(drop=True)
    out = []
    for sym, g in df.groupby("symbol", sort=False):
        cur = None
        for r in g.itertuples(index=False):
            if cur is not None and r.effective_from <= cur[2] + pd.Timedelta(days=1):
                cur[2] = max(cur[2], r.effective_to)
                if r.note and r.note not in cur[3]:
                    cur[3] = (cur[3] + " | " + r.note)[:200]
            else:
                if cur is not None:
                    out.append(tuple(cur))
                cur = [sym, r.effective_from, r.effective_to, r.note]
        out.append(tuple(cur))
    return pd.DataFrame(out, columns=["symbol", "effective_from", "effective_to", "note"])


def main():
    os.makedirs(OUT, exist_ok=True)
    ident = Identity()
    summary = []
    for idx, size in SIZE.items():
        df = apply_overrides(spells_for(idx))
        df["symbol"] = df["symbol"].map(ident.canonical)
        df = merge_spells(df)
        df = df[df["effective_to"] > df["effective_from"]]
        out = df.copy()
        out["effective_to"] = out["effective_to"].where(out["effective_to"] < FAR, pd.NaT)
        out["effective_from"] = out["effective_from"].dt.date; out["effective_to"] = out["effective_to"].dt.date
        out.to_csv(f"{OUT}/{idx}.csv", index=False)
        # member count on every event date from 2006
        dates = sorted(d for d in set(df["effective_from"]) | set(df["effective_to"]) if pd.Timestamp("2006-01-01") <= d < FAR)
        counts = [(d.date(), int(((df["effective_from"] <= d) & (df["effective_to"] > d)).sum())) for d in dates]
        off = [(d, n) for d, n in counts if abs(n - size) > 1]
        summary.append((idx, len(df), df["symbol"].nunique(), len(counts), min(n for _, n in counts), max(n for _, n in counts), len(off)))
        if off:
            print(f"  {idx}: {len(off)} dates off by >1: {off[:6]}")
    print(pd.DataFrame(summary, columns=["index", "rows", "symbols", "event_dates", "min_members", "max_members", "dates_off_by>1"]).to_string(index=False))


if __name__ == "__main__":
    main()
