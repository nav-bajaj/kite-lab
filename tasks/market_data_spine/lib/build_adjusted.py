"""Phase 4: adjusted views from the raw layer and the filings table (D-2:
store raw, adjust on read — materialised here so a backtest reads one file).

For each company series in prices/bhavcopy/, the events of every ISIN and
ticker it traded under are collected from corporate_actions.csv, and a
cumulative back-adjustment factor is built: history before an ex-date is
multiplied by that event's factor, events compounding backwards.

  bonus A:B        B/(A+B)
  split X->Y       Y/X          (consolidation likewise, Y/X > 1)
  rights A:B @P    ((B*Pcum) + A*(face+P)) / ((A+B)*Pcum)   Pcum = raw close on the cum day
  dividend D       (Pcum - D)/Pcum            total-return view only
  demerger         measured: raw close ex-day / raw close cum-day, applied
                   only when the drop is > 5% (below that the filing was a
                   non-event for the listed line); logged either way

Two views are written from one pass:
  prices/adjusted_pr/<SYM>.csv   price return  — splits, bonus, rights, demergers
  prices/adjusted_tr/<SYM>.csv   total return  — the above plus cash dividends
Both carry the cumulative factor columns so the adjustment is auditable
row by row. Volume is scaled by the inverse of the share-count factor.
"""
from __future__ import annotations

import glob, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from identity import Identity

REPO = "/Users/navdeep/kite-lab"
MASTER = f"{REPO}/data/master"
RAW = f"{MASTER}/prices/bhavcopy"
OUT_PR = f"{MASTER}/prices/adjusted_pr"
OUT_TR = f"{MASTER}/prices/adjusted_tr"
SHARE_TYPES = {"bonus", "split", "consolidation", "rights"}


def event_factor(e, p_cum: float):
    """-> (factor, share_count_factor_or_None, note)"""
    t = e.type
    if t in ("bonus", "split", "consolidation"):
        f = float(e.factor_or_amount); return f, f, ""
    if t == "rights":
        try:
            ab, pr = str(e.detail).split("@prem=")
            a, b = [int(x) for x in ab.split(":")]; prem = None if pr == "None" else float(pr)
        except Exception:  # noqa: BLE001
            return 1.0, None, "rights:unparsed"
        if prem is None:
            return 1.0, None, "rights:no-price"
        fv = float(str(e.face_val).replace(",", "")) if pd.notna(e.face_val) and str(e.face_val).replace(",", "").replace(".", "").isdigit() else 0.0
        issue = fv + prem
        f = (b * p_cum + a * issue) / ((a + b) * p_cum)
        return min(f, 1.0), b / (a + b), ""
    if t == "dividend":
        d = float(e.factor_or_amount) if pd.notna(e.factor_or_amount) else None
        if d is None or d <= 0 or d >= p_cum:
            return 1.0, None, "dividend:unparsed-or-implausible"
        return (p_cum - d) / p_cum, None, ""
    return 1.0, None, t


def adjust_one(df: pd.DataFrame, events: pd.DataFrame, log: list, key: str):
    df = df.sort_values("date").reset_index(drop=True)
    dates = df["date"].values
    f_pr = np.ones(len(df)); f_tr = np.ones(len(df)); f_vol = np.ones(len(df))
    for e in events.sort_values("ex_date").itertuples():
        ex = np.datetime64(e.ex_date)
        i = np.searchsorted(dates, ex)           # first row on/after the ex-date
        if i == 0 or i >= len(df):
            continue                             # event outside the series
        p_cum = float(df.loc[i - 1, "close"])
        if p_cum <= 0:
            continue
        if e.type == "demerger":
            p_ex = float(df.loc[i, "close"]); f = p_ex / p_cum
            if f < 0.95:
                f_pr[:i] *= f; f_tr[:i] *= f; log.append((key, str(e.ex_date), "demerger", round(f, 5), "measured"))
            else:
                log.append((key, str(e.ex_date), "demerger", round(f, 5), "ignored:<5%"))
            continue
        f, fs, note = event_factor(e, p_cum)
        if note:
            log.append((key, str(e.ex_date), e.type, None, note)); continue
        if e.type == "dividend":
            f_tr[:i] *= f
        else:
            f_pr[:i] *= f; f_tr[:i] *= f
        if fs:
            f_vol[:i] /= fs
    return f_pr, f_tr, f_vol


def main():
    os.makedirs(OUT_PR, exist_ok=True); os.makedirs(OUT_TR, exist_ok=True)
    ca = pd.read_csv(f"{MASTER}/corporate_actions.csv", parse_dates=["ex_date"])
    ca["ex_date"] = ca["ex_date"].dt.date
    ca_by_isin = {k: g for k, g in ca.groupby("isin")}
    ca_by_sym = {k: g for k, g in ca.groupby("symbol")}
    ident = Identity()
    if ident.overlaps:
        pd.DataFrame(ident.overlaps, columns=["symbol_a", "symbol_b", "from", "to"]).to_csv(f"{MASTER}/qa/identity_overlaps.csv", index=False)
        print(f"  identity overlaps flagged: {len(ident.overlaps)} (qa/identity_overlaps.csv)")
    log, n = [], 0
    files = sorted(glob.glob(f"{RAW}/*.csv"))
    for i, f in enumerate(files, 1):
        key = os.path.basename(f)[:-4]
        df = pd.read_csv(f, parse_dates=["date"])
        # events by the ISIN each window carried (bhavcopy rows lack ISIN before
        # 2011-06, so the window's ISIN from the symbol master fills that in),
        # then by symbol only for windows with no known ISIN
        parts = []
        wins = ident.w[ident.w["company"].isin(ident.companies(key))] if ident.companies(key) else ident.w.iloc[0:0]
        for wnd in wins.itertuples():
            lo, hi = wnd.first_seen - pd.Timedelta(days=30), wnd.last_seen + pd.Timedelta(days=30)
            if not str(wnd.isin).startswith("SYM:") and wnd.isin in ca_by_isin:
                g = ca_by_isin[wnd.isin]
            elif wnd.symbol in ca_by_sym:
                g = ca_by_sym[wnd.symbol]
            else:
                continue
            g = g[(pd.to_datetime(g["ex_date"]) >= lo) & (pd.to_datetime(g["ex_date"]) <= hi)]
            parts.append(g)
        if not parts and key in ca_by_sym:
            parts.append(ca_by_sym[key])
        ev = pd.concat(parts) if parts else ca.iloc[0:0]
        # one event per (ex-date, type): the same filing can arrive under two keys
        ev = ev.sort_values("factor_or_amount").drop_duplicates(["ex_date", "type"], keep="first") if len(ev) else ev
        f_pr, f_tr, f_vol = adjust_one(df, ev, log, key)
        base = df[["date", "open", "high", "low", "close", "volume", "traded_as"]].copy()
        for out, fac in ((OUT_PR, f_pr), (OUT_TR, f_tr)):
            a = base.copy()
            for c in ("open", "high", "low", "close"):
                a[c] = (df[c] * fac).round(4)
            a["volume"] = (df["volume"] * f_vol).round(0)
            a["factor"] = fac.round(8)
            a.to_csv(f"{out}/{key}.csv", index=False)
        n += 1
        if i % 300 == 0:
            print(f"  {i}/{len(files)}", flush=True)
    lg = pd.DataFrame(log, columns=["symbol", "ex_date", "type", "factor", "note"])
    lg.to_csv(f"{MASTER}/qa/adjustment_log.csv", index=False)
    print(f"adjusted {n} series -> adjusted_pr/, adjusted_tr/")
    print(lg.groupby(["type", "note"]).size().to_string())


if __name__ == "__main__":
    main()
