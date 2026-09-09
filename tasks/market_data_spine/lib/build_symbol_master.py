"""Build the ISIN-keyed symbol master from bhavcopy + NSE corporate filings,
then resolve the company names the index reconstruction could not map.

Inputs
  data/master/raw/bhavcopy/<YYYY>/<date>_<fmt>.zip   every cash-market day
  data/master/raw/nse_ca/<YYYY>Q<n>.json               every filing, 2000 ->
  tasks/index_reconstruction/data/{unresolved_symbols,*_unresolved}.csv

Outputs (data/master/)
  bhavcopy_eq.parquet      date, symbol, series, isin, o/h/l/c/last/prevclose/volume
  symbol_master.csv        isin, symbol, first_seen, last_seen, n_days
  isin_names.csv           isin, name, first_seen, last_seen, n_filings
  resolution.csv           one row per (index, unresolved name): isin, symbol, method

Why ISIN. A symbol is reused (a delisted ticker can be reassigned) and a
company is renamed; the ISIN is the only key that is stable across both. The
bhavcopy says which symbol carried which ISIN on which day; the filings say
which company name the ISIN belonged to. Pre-ISIN bhavcopies (before the
column appeared) are keyed by symbol and joined forward to the ISIN that
symbol carries when the column arrives, provided the two windows abut.

Name matching is exact on a normalised form first, then strict token
equality. Nothing fuzzier: the reconstruction already showed a permissive
matcher scoring Dena Bank onto D B Corp at 1.0.
"""
from __future__ import annotations

import glob, io, json, os, re, sys, zipfile
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manual_resolutions import BY_NAME, SYMBOL_HINTS

REPO = "/Users/navdeep/kite-lab"
RAW_BHAV = f"{REPO}/data/master/raw/bhavcopy"
RAW_CA = f"{REPO}/data/master/raw/nse_ca"
RAW_MASTERS = f"{REPO}/data/master/raw/nse_masters"
OUT = f"{REPO}/data/master"
RECON = f"{REPO}/tasks/index_reconstruction/data"
EQ_SERIES = {"EQ", "BE", "BZ", "BL", "B1", "B2", "SM", "ST"}   # cash equity + SME


def _norm(t: str) -> str:
    t = t.lower().replace("&", " and ")
    t = re.sub(r"\b(ltd|limited|co|company|corporation|corp|the|inc)\b", " ", t)
    return re.sub(r"[^a-z0-9]", "", t)


def _tokens(t: str) -> frozenset:
    t = t.lower().replace("&", " and ")
    t = re.sub(r"\b(ltd|limited|co|company|corporation|corp|the|inc|of|india|indian)\b", " ", t)
    return frozenset(w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 1)


# ---------------------------------------------------------------- bhavcopy
def read_legacy(raw: bytes, day: pd.Timestamp) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"SYMBOL": "symbol", "SERIES": "series", "OPEN": "open", "HIGH": "high",
                            "LOW": "low", "CLOSE": "close", "LAST": "last", "PREVCLOSE": "prevclose",
                            "TOTTRDQTY": "volume", "TIMESTAMP": "date", "ISIN": "isin"})
    if "isin" not in df.columns:
        df["isin"] = None
    df["date"] = day          # filename date; the TIMESTAMP column has mixed 2- and 4-digit years
    return df[["date", "symbol", "series", "isin", "open", "high", "low", "close", "last", "prevclose", "volume"]]


def read_udiff(raw: bytes, day: pd.Timestamp) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw), low_memory=False)
    df = df[df["Sgmt"] == "CM"]
    df = df.rename(columns={"TckrSymb": "symbol", "SctySrs": "series", "OpnPric": "open", "HghPric": "high",
                            "LwPric": "low", "ClsPric": "close", "LastPric": "last", "PrvsClsgPric": "prevclose",
                            "TtlTradgVol": "volume", "TradDt": "date", "ISIN": "isin", "FinInstrmNm": "name"})
    df["date"] = day
    return df[["date", "symbol", "series", "isin", "open", "high", "low", "close", "last", "prevclose", "volume", "name"]]


def load_bhavcopy() -> tuple[pd.DataFrame, pd.DataFrame]:
    frames, udiff_names = [], []
    files = sorted(glob.glob(f"{RAW_BHAV}/*/*.zip"))
    for i, f in enumerate(files):
        fmt = "udiff" if f.endswith("_udiff.zip") else "legacy"
        try:
            with zipfile.ZipFile(f) as z:
                raw = z.read(z.namelist()[0])
        except zipfile.BadZipFile:
            print(f"  bad zip: {f}", file=sys.stderr); continue
        day = pd.Timestamp(os.path.basename(f)[:10])
        df = read_udiff(raw, day) if fmt == "udiff" else read_legacy(raw, day)
        df["series"] = df["series"].astype(str).str.strip()
        df = df[df["series"].isin(EQ_SERIES)]
        df["symbol"] = df["symbol"].astype(str).str.strip()
        if "name" in df.columns:
            udiff_names.append(df[["date", "isin", "name"]])
            df = df.drop(columns=["name"])
        frames.append(df)
        if (i + 1) % 500 == 0:
            print(f"  bhavcopy {i+1}/{len(files)}", flush=True)
    eq = pd.concat(frames, ignore_index=True)
    eq["isin"] = eq["isin"].where(eq["isin"].notna() & (eq["isin"].astype(str).str.len() == 12), None)
    names = pd.concat(udiff_names, ignore_index=True) if udiff_names else pd.DataFrame(columns=["date", "isin", "name"])
    return eq, names


def symbol_windows(eq: pd.DataFrame, sightings: pd.DataFrame) -> pd.DataFrame:
    """(isin, symbol) -> first/last traded. Bhavcopy rows with an ISIN are the
    primary evidence. Pre-ISIN bhavcopy rows are keyed by symbol and assigned
    the ISIN that filings show the symbol carried at the time; failing that,
    the ISIN the same symbol carries when the column arrives, if the windows
    abut within 60 days. Filing sightings alone never create a traded window
    (a filing is not a trade) but do extend first_seen where they predate the
    bhavcopy archive."""
    with_isin = eq[eq["isin"].notna()]
    w = (with_isin.groupby(["isin", "symbol"])["date"]
         .agg(first_seen="min", last_seen="max", n_days="count").reset_index())
    no_isin = eq[eq["isin"].isna()]
    if len(no_isin):
        # per (symbol, year) block, ask the filings which ISIN that symbol carried
        blk = no_isin.assign(year=no_isin["date"].dt.year)
        w0 = (blk.groupby(["symbol", "year"])["date"]
              .agg(first_seen="min", last_seen="max", n_days="count").reset_index())
        sg = sightings.assign(year=sightings["date"].dt.year)
        sy = (sg.groupby(["symbol", "year"])["isin"]
              .agg(lambda s: set(s)).reset_index().rename(columns={"isin": "isin_set"}))
        w0 = w0.merge(sy, on=["symbol", "year"], how="left")
        # widen: a symbol with exactly one ISIN across ALL filings gets it everywhere
        one = sightings.groupby("symbol")["isin"].agg(lambda s: set(s))
        one = one[one.apply(len) == 1].apply(lambda s: next(iter(s)))
        w0["isin"] = w0["isin_set"].apply(lambda s: next(iter(s)) if isinstance(s, set) and len(s) == 1 else None)
        w0["isin"] = w0["isin"].fillna(w0["symbol"].map(one))
        # fallback: forward-abut to the ISIN the symbol carries once the column exists
        later = w.groupby("symbol").agg(isin_set2=("isin", lambda s: set(s)),
                                        isin_first=("first_seen", "min")).reset_index()
        w0 = w0.merge(later, on="symbol", how="left")
        fb = (w0["isin"].isna()
              & w0["isin_set2"].apply(lambda s: isinstance(s, set) and len(s) == 1)
              & ((w0["isin_first"] - w0["last_seen"]).dt.days.between(-5, 400)))
        w0.loc[fb, "isin"] = w0.loc[fb, "isin_set2"].apply(lambda s: next(iter(s)))
        # propagate backwards through contiguous yearly blocks of the same symbol:
        # a block with no ISIN inherits from the following year's block when the
        # two abut (gap <= 120 days). A reused symbol shows up as a multi-year gap
        # and is not bridged.
        w0 = w0.sort_values(["symbol", "year"]).reset_index(drop=True)
        changed = True
        while changed:
            changed = False
            nxt = w0.shift(-1)
            same = (nxt["symbol"] == w0["symbol"])
            abut = (nxt["first_seen"] - w0["last_seen"]).dt.days.between(-5, 120)
            take = w0["isin"].isna() & same & abut & nxt["isin"].notna()
            if take.any():
                w0.loc[take, "isin"] = nxt.loc[take, "isin"]
                changed = True
        # renames from NSE's symbol-change master: a block of the OLD symbol that
        # ends at the change date inherits the ISIN the NEW symbol carries first
        # afterwards. Processed newest-first so A->B->C chains resolve.
        chg = load_symbol_changes()
        det = detect_renames(eq)
        det.to_csv(f"{OUT}/symbol_renames_detected.csv", index=False)
        known = set(zip(chg["old"], chg["new"]))
        extra = det[[ (o, n) not in known for o, n in zip(det["old"], det["new"]) ]]
        print(f"    rename detector: {len(det)} PREVCLOSE-matched renames, {len(extra)} not in NSE's master", flush=True)
        chg = pd.concat([chg, pd.DataFrame({"company": "", "old": extra["old"], "new": extra["new"], "date": extra["t1"]})],
                        ignore_index=True)
        earliest_isin = {}
        for r in pd.concat([w[["symbol", "isin", "first_seen"]],
                            w0.dropna(subset=["isin"])[["symbol", "isin", "first_seen"]]]).sort_values("first_seen").itertuples():
            earliest_isin.setdefault(r.symbol, []).append((r.first_seen, r.isin))
        n_chain = 0
        for _ in range(4):
            for r in chg.sort_values("date", ascending=False).itertuples():
                cands = [i for d, i in earliest_isin.get(r.new, []) if d >= r.date - pd.Timedelta(days=30)]
                if not cands:
                    cands = [i for d, i in earliest_isin.get(r.new, [])]
                if not cands:
                    continue
                isin = cands[0]
                take = (w0["symbol"] == r.old) & w0["isin"].isna() & (w0["last_seen"] <= r.date + pd.Timedelta(days=30))
                if take.any():
                    w0.loc[take, "isin"] = isin; n_chain += int(take.sum())
                    for fs in w0.loc[take, "first_seen"]:
                        earliest_isin.setdefault(r.old, []).append((fs, isin))
                    earliest_isin[r.old].sort()
        print(f"    symbol-change master: {len(chg)} renames, {n_chain} pre-ISIN blocks chained", flush=True)
        # then propagate backwards again through contiguous blocks
        changed = True
        while changed:
            changed = False
            nxt = w0.shift(-1)
            same = (nxt["symbol"] == w0["symbol"])
            abut = (nxt["first_seen"] - w0["last_seen"]).dt.days.between(-5, 120)
            take = w0["isin"].isna() & same & abut & nxt["isin"].notna()
            if take.any():
                w0.loc[take, "isin"] = nxt.loc[take, "isin"]; changed = True
        w0["isin"] = w0["isin"].fillna("SYM:" + w0["symbol"])       # symbol-only, never joined
        w = pd.concat([w, w0[w.columns]], ignore_index=True)
    # merge abutting windows of the same (isin, symbol) produced by the join
    w = (w.groupby(["isin", "symbol"])
         .agg(first_seen=("first_seen", "min"), last_seen=("last_seen", "max"), n_days=("n_days", "sum"))
         .reset_index().sort_values(["isin", "first_seen"]))
    return w


# ---------------------------------------------------------------- rename detector
def detect_renames(eq: pd.DataFrame) -> pd.DataFrame:
    """Ticker renames the symbol-change master does not list, read off the
    bhavcopy itself: when symbol A stops trading and symbol B starts within 45
    days with B's first PREVCLOSE equal to A's last CLOSE (to 0.5%), and B never
    traded before, that is one company changing ticker. Exact-price collisions
    between unrelated symbols on the same day are rare but possible, so a match
    is rejected if more than one B (or more than one A) qualifies."""
    g = eq.sort_values("date").groupby("symbol")
    first = g.first()[["date", "prevclose"]].rename(columns={"date": "t1", "prevclose": "pc"})
    last = g.last()[["date", "close"]].rename(columns={"date": "t0", "close": "c"})
    counts = g.size()
    first = first[counts >= 20]; last = last[counts >= 20]          # ignore one-week wonders
    end = eq["date"].max()
    last = last[last["t0"] < end - pd.Timedelta(days=10)]            # A actually stopped
    first = first[first["t1"] > eq["date"].min() + pd.Timedelta(days=10)]  # B actually started
    a = last.reset_index().rename(columns={"symbol": "old"})
    b = first.reset_index().rename(columns={"symbol": "new"})
    a["key"] = 1; b["key"] = 1
    a["t0_month"] = a["t0"].dt.to_period("M"); b["t1_month"] = b["t1"].dt.to_period("M")
    # candidate join on month proximity keeps the cross join small
    pairs = []
    for off in (0, 1, 2):
        bb = b.copy(); bb["t0_month"] = bb["t1_month"] - off
        pairs.append(a.merge(bb, on=["t0_month", "key"]))
    m = pd.concat(pairs, ignore_index=True)
    m = m[(m["t1"] > m["t0"]) & ((m["t1"] - m["t0"]).dt.days <= 45) & (m["old"] != m["new"])]
    m = m[(m["c"] > 0) & ((m["pc"] / m["c"] - 1).abs() <= 0.005)]
    # uniqueness both ways
    m = m[~m.duplicated("old", keep=False) & ~m.duplicated("new", keep=False)]
    return m[["old", "new", "t0", "t1", "c", "pc"]].sort_values("t1").reset_index(drop=True)


# ---------------------------------------------------------------- NSE masters
def load_symbol_changes() -> pd.DataFrame:
    """NSE's symbol-change master: company, old symbol, new symbol, date. The
    filings API stamps today's symbol on every historical filing, so this file
    is the only source that dates a ticker rename before the bhavcopy carried
    ISIN (2011-06)."""
    df = pd.read_csv(f"{RAW_MASTERS}/symbolchange.csv", header=None,
                     names=["company", "old", "new", "date"], skipinitialspace=True)
    df["old"] = df["old"].astype(str).str.strip(); df["new"] = df["new"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"].str.strip(), format="%d-%b-%Y", errors="coerce")
    return df.dropna(subset=["date"]).sort_values("date")


def load_name_masters() -> pd.DataFrame:
    """Company names by symbol from NSE's name-change master (previous and new
    names, dated) and the current listing file. -> rows of (name, symbol, date)."""
    nc = pd.read_csv(f"{RAW_MASTERS}/namechange.csv", skipinitialspace=True)
    nc.columns = [c.strip() for c in nc.columns]
    nc["date"] = pd.to_datetime(nc["NCH_DT"].astype(str).str.strip(), format="%d-%b-%Y", errors="coerce")
    a = nc[["NCH_PREV_NAME", "NCH_SYMBOL", "date"]].rename(columns={"NCH_PREV_NAME": "name", "NCH_SYMBOL": "symbol"})
    b = nc[["NCH_NEW_NAME", "NCH_SYMBOL", "date"]].rename(columns={"NCH_NEW_NAME": "name", "NCH_SYMBOL": "symbol"})
    eqL = pd.read_csv(f"{RAW_MASTERS}/EQUITY_L.csv", skipinitialspace=True)
    eqL.columns = [c.strip() for c in eqL.columns]
    c = eqL[["NAME OF COMPANY", "SYMBOL"]].rename(columns={"NAME OF COMPANY": "name", "SYMBOL": "symbol"})
    c["date"] = pd.Timestamp.today().normalize()
    df = pd.concat([a, b, c], ignore_index=True).dropna(subset=["name", "symbol"])
    df["name"] = df["name"].astype(str).str.strip(); df["symbol"] = df["symbol"].astype(str).str.strip()
    return df


# ---------------------------------------------------------------- filings
def load_filing_names() -> tuple[pd.DataFrame, pd.DataFrame]:
    """-> (names by ISIN, symbol sightings by ISIN). Filings carry symbol + ISIN
    per event from 2000, which dates symbol windows before the bhavcopy had an
    ISIN column."""
    rows = []
    for f in sorted(glob.glob(f"{RAW_CA}/*.json")):
        for r in json.load(open(f)):
            isin, name, sym = r.get("isin"), r.get("comp"), r.get("symbol")
            d = r.get("exDate") or r.get("recDate") or r.get("bcStartDate")
            if not isin or not name or not d or d == "-":
                continue
            rows.append((isin, name.strip(), sym, pd.to_datetime(d, format="%d-%b-%Y", errors="coerce")))
    df = pd.DataFrame(rows, columns=["isin", "name", "symbol", "date"]).dropna(subset=["date"])
    sightings = df.dropna(subset=["symbol"])[["isin", "symbol", "date"]]
    sightings = sightings[sightings["symbol"].astype(str).str.strip() != ""]
    return (df.groupby(["isin", "name"])
            .agg(first_seen=("date", "min"), last_seen=("date", "max"), n_filings=("date", "count"),
                 symbols=("symbol", lambda s: "|".join(sorted(set(x for x in s if x)))))
            .reset_index()), sightings


# ---------------------------------------------------------------- resolution
def resolve_names(names: pd.DataFrame, windows: pd.DataFrame, name_masters: pd.DataFrame) -> pd.DataFrame:
    """For each unresolved (index, company_name, from, to): find the ISIN whose
    filing name matches and whose activity overlaps the spell, then the
    symbol(s) that ISIN traded under during the spell."""
    by_norm = defaultdict(set)
    by_tok = defaultdict(set)
    for r in names.itertuples():
        by_norm[_norm(r.name)].add(r.isin)
        by_tok[_tokens(r.name)].add(r.isin)
    act = names.groupby("isin").agg(a0=("first_seen", "min"), a1=("last_seen", "max"))
    nm_by_norm, nm_by_tok = defaultdict(set), defaultdict(set)
    for r in name_masters.itertuples():
        nm_by_norm[_norm(r.name)].add(r.symbol)
        nm_by_tok[_tokens(r.name)].add(r.symbol)
    out = []
    targets = []
    for idx, path in [("nse500", "unresolved_symbols.csv"), ("nifty50", "nifty50_unresolved.csv"),
                      ("nifty100", "nifty100_unresolved.csv"), ("nifty250", "nifty250_unresolved.csv")]:
        p = f"{RECON}/{path}"
        if not os.path.exists(p):
            continue
        u = pd.read_csv(p)
        u.columns = [c.strip() for c in u.columns]
        for r in u.itertuples(index=False):
            targets.append((idx, r[0], pd.Timestamp(r[1]), pd.Timestamp(r[2]) if pd.notna(r[2]) else pd.Timestamp("2099-12-31")))
    for idx, name, d0, d1 in targets:
        if name in BY_NAME:
            cands, method = {BY_NAME[name]}, "manual-isin"
        elif name in SYMBOL_HINTS:
            hit = windows[windows["symbol"].isin(SYMBOL_HINTS[name])
                          & (windows["first_seen"] <= d1) & (windows["last_seen"] >= d0)]
            cands, method = set(hit["isin"]), "manual-symbol"
        else:
            cands, method = by_norm.get(_norm(name), set()), "norm-exact"
            if not cands:
                cands, method = by_tok.get(_tokens(name), set()), "token-exact"
            if not cands:
                # NSE name-change / listing masters give a SYMBOL; take the ISIN(s)
                # that symbol traded under during the spell
                syms = nm_by_norm.get(_norm(name)) or nm_by_tok.get(_tokens(name)) or set()
                hit = windows[windows["symbol"].isin(syms) & ~windows["isin"].str.startswith("SYM:")
                              & (windows["first_seen"] <= d1) & (windows["last_seen"] >= d0)]
                cands, method = set(hit["isin"]), "namechange-master"
        # keep ISINs whose filing activity overlaps the spell, generously
        if not method.startswith("manual") and method != "namechange-master":
            cands = [i for i in cands if i in act.index
                     and act.loc[i, "a0"] <= d1 + pd.Timedelta(days=730)
                     and act.loc[i, "a1"] >= d0 - pd.Timedelta(days=730)]
        cands = list(cands)
        if len(cands) > 1:
            # a face-value change issues a new ISIN for the same company; if every
            # candidate's filing names normalise to one company, keep them all
            nm = {_norm(n) for i in cands for n in names.loc[names["isin"] == i, "name"]}
            if len(nm) <= 2 and len({_tokens(n) for i in cands for n in names.loc[names["isin"] == i, "name"]}) <= 2:
                method = method + "+isin-set"
            else:
                out.append((idx, name, d0.date(), d1.date(), None, None, None, None, "ambiguous", "|".join(cands)))
                continue
        if not cands:
            out.append((idx, name, d0.date(), d1.date(), None, None, None, None, "unresolved", ""))
            continue
        isin = cands[0]
        w = windows[windows["isin"].isin(cands) & (windows["first_seen"] <= d1) & (windows["last_seen"] >= d0)]
        if w.empty:
            # a face-value change issues a new ISIN under the same symbol; follow the
            # symbol(s) the filings and bhavcopy attach to these ISINs into the spell
            syms = set(windows.loc[windows["isin"].isin(cands), "symbol"])
            for i in cands:
                for sy in names.loc[names["isin"] == i, "symbols"].dropna():
                    syms |= set(str(sy).split("|"))
            syms.discard(""); syms.discard("nan")
            w = windows[windows["symbol"].isin(syms) & (windows["first_seen"] <= d1) & (windows["last_seen"] >= d0)]
            if not w.empty:
                method = method + "+symbol-chain"
        if w.empty:
            # ISIN known but never traded under any symbol in the spell (pre-2005 spells)
            wl = windows[windows["isin"].isin(cands)]
            out.append((idx, name, d0.date(), d1.date(), isin, "|".join(wl["symbol"]), None, None,
                        "isin-only", ""))
            continue
        for s in w.itertuples():
            out.append((idx, name, d0.date(), d1.date(), s.isin, s.symbol,
                        max(s.first_seen, d0).date(), min(s.last_seen, d1).date(), method, ""))
    return pd.DataFrame(out, columns=["index", "company_name", "spell_from", "spell_to", "isin", "symbol",
                                      "symbol_from", "symbol_to", "method", "candidates"])


def main():
    os.makedirs(OUT, exist_ok=True)
    print("[1] bhavcopy ...", flush=True)
    eq, udiff_names = load_bhavcopy()
    print(f"    {len(eq):,} equity rows, {eq['date'].min().date()} -> {eq['date'].max().date()}, "
          f"{eq['date'].nunique()} days, ISIN present on {eq['isin'].notna().mean():.0%} of rows")
    first_isin = eq.loc[eq["isin"].notna(), "date"].min()
    print(f"    first bhavcopy day with ISIN: {first_isin.date() if pd.notna(first_isin) else None}")
    eq.to_parquet(f"{OUT}/bhavcopy_eq.parquet", index=False)

    print("[2] filing names + symbol sightings ...", flush=True)
    names, sightings = load_filing_names()
    print(f"    {len(sightings):,} symbol sightings in filings, "
          f"{sightings['date'].min().date()} -> {sightings['date'].max().date()}")

    print("[3] symbol windows ...", flush=True)
    windows = symbol_windows(eq, sightings)
    windows.to_csv(f"{OUT}/symbol_master.csv", index=False)
    load_symbol_changes().to_csv(f"{OUT}/symbol_changes.csv", index=False)
    print(f"    {len(windows):,} (isin, symbol) windows; {windows['isin'].nunique():,} ISINs; "
          f"{(windows['isin'].str.startswith('SYM:')).sum()} symbol-only (never joined to an ISIN)")

    print("[4] names ...", flush=True)
    if len(udiff_names):
        un = (udiff_names.dropna().groupby(["isin", "name"])["date"]
              .agg(first_seen="min", last_seen="max", n_filings="count").reset_index())
        un["symbols"] = ""
        names = pd.concat([names, un], ignore_index=True)
        names = (names.groupby(["isin", "name"])
                 .agg(first_seen=("first_seen", "min"), last_seen=("last_seen", "max"),
                      n_filings=("n_filings", "sum"), symbols=("symbols", "first")).reset_index())
    names.to_csv(f"{OUT}/isin_names.csv", index=False)
    print(f"    {len(names):,} (isin, name) pairs over {names['isin'].nunique():,} ISINs, "
          f"{names['first_seen'].min().date()} -> {names['last_seen'].max().date()}")

    print("[5] resolve reconstruction leftovers ...", flush=True)
    res = resolve_names(names, windows, load_name_masters())
    res.to_csv(f"{OUT}/resolution.csv", index=False)
    summ = res.groupby(["index", "method"]).size().unstack(fill_value=0)
    print(summ.to_string())
    ok = res[res["method"].str.replace("+isin-set", "", regex=False).str.replace("+symbol-chain", "", regex=False).isin(["norm-exact", "token-exact", "manual-isin", "manual-symbol", "namechange-master"])]
    print(f"    resolved to a traded symbol: {ok.groupby('index')['company_name'].nunique().to_dict()}")


if __name__ == "__main__":
    main()
