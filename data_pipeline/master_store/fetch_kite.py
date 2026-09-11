"""Pull Kite's adjusted daily history, fresh, for every index member Kite
can serve. Phase 3 of the market data spine (D-6, D-7).

Targets: every symbol in the four reconstructed membership files plus every
resolved leftover, mapped through the symbol master to the ticker each ISIN
trades under TODAY (Kite keys on the live tradingsymbol and serves the whole
listed life under it: INFOSYSTCH's years arrive under INFY). NSE first, BSE
where NSE has no instrument. Anything on neither is left for the bhavcopy.

Output: data/master/prices/kite/<SYMBOL>.csv as served, and manifest entries
with the pull timestamp and a hash, because a later dividend rewrites the
whole series and the store is versioned by pull (D-6). Resumable: a symbol
with a file from this pull date is skipped.
"""
from __future__ import annotations

import argparse, hashlib, json, os, sys, time
from datetime import date, timedelta

import pandas as pd

from data_pipeline.master_store import ROOT as REPO, MASTER  # noqa: E402
sys.path.insert(0, REPO); sys.path.insert(0, f"{REPO}/scripts")  # scripts.history_utils
os.chdir(REPO)
from scripts.history_utils import init_kite_client, fetch_history, RateLimiter  # noqa: E402

OUT = f"{MASTER}/prices/kite"
MANIFEST = f"{MASTER}/prices/kite_manifest.json"
RECON = f"{REPO}/tasks/index_reconstruction/data"
MASTER = MASTER
START = "2000-01-01"


def build_targets() -> pd.DataFrame:
    win = pd.read_csv(f"{MASTER}/symbol_master.csv", parse_dates=["first_seen", "last_seen"])
    win = win[~win["isin"].str.startswith("SYM:")]
    syms = set()
    for f in ["nse500", "nifty50", "nifty100", "nifty250"]:
        recon = f"{RECON}/{f}_membership_reconstructed.csv"
        # the reconstruction files live only on the research machine; in production the store's own point-in-time
        # membership files carry the same canonical symbols (P1, 2026-09-11)
        src = recon if os.path.exists(recon) else f"{MASTER}/membership/{f}.csv"
        syms |= set(pd.read_csv(src)["symbol"])
    res = pd.read_csv(f"{MASTER}/resolution.csv")
    syms |= set(res["symbol"].dropna())
    # symbol -> ISINs -> every symbol under those ISINs -> the latest-traded one
    isins_of = win.groupby("symbol")["isin"].agg(set)
    latest_by_isin = win.sort_values("last_seen").groupby("isin").last()["symbol"]
    ins = pd.read_csv(f"{REPO}/data/instruments_full.csv")
    ins = ins[ins["instrument_type"] == "EQ"]
    nse = set(ins[ins["exchange"] == "NSE"]["tradingsymbol"]); bse = set(ins[ins["exchange"] == "BSE"]["tradingsymbol"])
    rows = {}
    for s in sorted(syms):
        cands = [s] + [latest_by_isin[i] for i in isins_of.get(s, set()) if i in latest_by_isin.index]
        for c in cands:
            if c in nse:
                rows[c] = ("NSE", s); break
            if c in bse:
                rows[c] = ("BSE", s); break
        else:
            rows[f"?{s}"] = ("NONE", s)
    df = pd.DataFrame([(k.lstrip("?"), v[0], v[1]) for k, v in rows.items()], columns=["symbol", "exchange", "from_symbol"])
    df = df.drop_duplicates("symbol")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=START)
    ap.add_argument("--symbols-file", default="", help="only these symbols (one per line); with --since-days 0 this is a full re-pull for them")
    ap.add_argument("--since-days", type=int, default=0, help="append mode: pull only the last N calendar days and merge into the existing file (nightly); 0 = full history")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    targets = build_targets()
    targets.to_csv(f"{MASTER}/kite_targets.csv", index=False)
    todo = targets[targets["exchange"] != "NONE"]
    if a.symbols_file:
        _want = set(l.strip() for l in open(a.symbols_file) if l.strip()); todo = todo[todo["symbol"].isin(_want)]
        print(f"  symbols-file: {len(todo)} symbols selected for a full re-pull")
    print(f"targets: {len(targets)} ({(targets['exchange']=='NSE').sum()} NSE, {(targets['exchange']=='BSE').sum()} BSE, "
          f"{(targets['exchange']=='NONE').sum()} not on Kite)", flush=True)
    if a.limit:
        todo = todo.head(a.limit)

    kite = init_kite_client()
    rl = RateLimiter(requests_per_second=3)
    raw_hist = kite.historical_data
    def limited(*args, **kw):
        for attempt in range(6):
            rl.acquire()
            try:
                return raw_hist(*args, **kw)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if "Too many requests" in msg or "429" in msg or "NetworkException" in type(e).__name__:
                    time.sleep(2 * (attempt + 1)); continue
                raise
        return raw_hist(*args, **kw)
    kite.historical_data = limited

    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    today = date.today().isoformat()
    n_ok = n_skip = n_err = 0
    t0 = time.time()
    for i, r in enumerate(todo.itertuples(), 1):
        path = f"{OUT}/{r.symbol}.csv"
        if not a.symbols_file and manifest.get(r.symbol, {}).get("pulled_at", "")[:10] == today and os.path.exists(path):   # a --symbols-file re-pull is always forced
            n_skip += 1; continue
        try:
            start = (date.today() - timedelta(days=a.since_days)).isoformat() if a.since_days else a.start

            df = fetch_history(kite, r.symbol, start, today, interval="day", exchange=r.exchange)

            if a.since_days and os.path.exists(path):

                old = pd.read_csv(path, parse_dates=["date"]); df = pd.concat([old[old["date"] < pd.Timestamp(start)], df]).drop_duplicates("date", keep="last").sort_values("date")
        except Exception as e:  # noqa: BLE001
            n_err += 1
            prev = manifest.get(r.symbol, {}); manifest[r.symbol] = {**prev, "exchange": r.exchange, "last_error": str(e)[:200], "last_error_at": today}   # keep first/last/rows
            print(f"  ERR {r.symbol} ({r.exchange}): {str(e)[:120]}", flush=True)
            continue
        if df.empty:
            n_err += 1
            prev = manifest.get(r.symbol, {}); manifest[r.symbol] = {**prev, "exchange": r.exchange, "last_error": "empty", "last_error_at": today}
            continue
        df = df[["date", "open", "high", "low", "close", "volume"]]
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        df.to_csv(path, index=False)
        h = hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
        manifest[r.symbol] = {"exchange": r.exchange, "from_symbol": r.from_symbol,
                              "first": str(df["date"].min().date()), "last": str(df["date"].max().date()),
                              "rows": int(len(df)), "sha256": h, "pulled_at": pd.Timestamp.now().isoformat(timespec="seconds"),
                              "basis": "kite-adjusted"}
        n_ok += 1
        if i % 50 == 0:
            json.dump(manifest, open(MANIFEST, "w"), indent=1)
            print(f"  {i}/{len(todo)} ok {n_ok} skip {n_skip} err {n_err} ({(time.time()-t0)/60:.1f} min)", flush=True)
    json.dump(manifest, open(MANIFEST, "w"), indent=1)
    print(f"done: ok {n_ok} skip {n_skip} err {n_err} in {(time.time()-t0)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
