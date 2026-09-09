"""Phase 4: a typed corporate-actions table from NSE's filings.

Every filing is one row of free text in `subject`. This parses the ones that
move a price series and drops the rest (AGMs, interest, buybacks, unit
distributions). One filing can carry several events ("Dividend Rs 5.50 And
Bonus 1:1"); each becomes its own row.

  dividend  amount per share. "Rs 12 Per Share" / "Re 0.50" / "Dividend-25%"
            (percent of the row's face value). Interim, final and special
            are all cash to the holder; type is kept for reference only.
  bonus     "Bonus A:B" -> A new shares per B held; price factor B/(A+B).
  split     "From Rs X ... To Rs Y" (also "Fv Split Rs.X To Rs.Y") -> factor
            Y/X. Consolidation is the same pattern with Y > X.
  rights    "Rights A:B @ Premium Rs P" -> A per B at face + P. The factor
            needs the cum price, so it is computed when applied, not here.
  demerger  no ratio in the filing; factor must be measured from the raw
            series (or entered by hand) when applied. Flagged, not silent.

Kite's own adjustment is measured against these events in verify_kite_adjustment.py
before the table is trusted to adjust anything.
"""
from __future__ import annotations

import glob, json, os, re
import numpy as np
import pandas as pd

REPO = "/Users/navdeep/kite-lab"
RAW = f"{REPO}/data/master/raw/nse_ca"
OUT = f"{REPO}/data/master/corporate_actions.csv"

NUM = r"(\d+(?:\.\d+)?)"
# NSE's older filings are abbreviated and run together: "Fv Splt Frm Rs 10 To Re 1",
# "Fv Spl-Rs10tore1/Bon-1:1", "Agm/Div-Rs10+Gld Jub-Rs10". Every pattern below
# tolerates missing spaces and the short forms Splt/Spl/Frm/Bon/Div.
RE_PCT = re.compile(r"dividend[^%\d]*?" + NUM + r"\s*%", re.I)
RE_AMT = re.compile(r"(?:rs|re|₹)\.?\s*" + NUM + r"\s*/?-?\s*(?:per|pr)\s*(?:share|sh|eq)", re.I)
RE_AMT2 = re.compile(r"div(?:idend)?[\s\-:/]*(?:final|interim|special|int|fin)?[\s\-:/]*(?:rs|re)\.?[\s\-:]*" + NUM, re.I)
RE_AMT3 = re.compile(r"(?:^|[/+ ])(?:[a-z ]{0,14})?(?:div|dividend)[^\d]{0,12}?" + NUM + r"(?!\s*%)(?!\s*:)", re.I)
RE_BONUS = re.compile(r"bon(?:us)?\s*[-:]?\s*(\d+)\s*:\s*(\d+)", re.I)
RE_SPLIT = re.compile(r"(?:fr(?:o)?m|spl(?:i)?t|sub[- ]?div(?:ision)?)[\s\-:]*(?:rs|re)?\.?\s*" + NUM
                      + r"\s*/?-?\s*(?:per\s*share)?\s*(?:to|-)\s*(?:rs|re)?\.?\s*" + NUM, re.I)
RE_SPLIT2 = re.compile(r"(?:rs|re)\.?\s*" + NUM + r"\s*to\s*(?:rs|re)\.?\s*" + NUM, re.I)
RE_RIGHTS = re.compile(r"rights?\s*[-:]?\s*(\d+)\s*:\s*(\d+)(?:\s*@?\s*premium\s*(?:of\s*)?(?:rs|re)\.?\s*" + NUM + r")?", re.I)


def parse(subject: str, face_val: str):
    s = subject.strip()
    low = s.lower()
    events = []
    if "demerger" in low:
        events.append(("demerger", None, ""))
    m = RE_BONUS.search(s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        events.append(("bonus", round(b / (a + b), 8), f"{a}:{b}"))
    m = RE_SPLIT.search(s) or (RE_SPLIT2.search(s) if re.search(r"spl|sub[- ]?div|consolidat|fv|face", low) else None)
    if m and re.search(r"spl|sub[- ]?div|consolidat|fv|face|frm|from", low):
        x, y = float(m.group(1)), float(m.group(2))
        if x > 0 and y > 0 and x != y:
            events.append(("split" if y < x else "consolidation", round(y / x, 8), f"{x:g}->{y:g}"))
    m = RE_RIGHTS.search(s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        prem = float(m.group(3)) if m.group(3) else None
        events.append(("rights", None, f"{a}:{b}@prem={prem}"))
    if "dividend" in low and "distribution" not in low:
        amt = 0.0; found = False
        for x in RE_AMT.findall(s):
            amt += float(x); found = True
        if not found:
            for x in RE_AMT2.findall(s):
                amt += float(x); found = True
        if not found and "%" not in low:
            for x in RE_AMT3.findall(s):
                amt += float(x); found = True
        if not found:
            try:
                fv = float(str(face_val).replace(",", ""))
            except ValueError:
                fv = None
            for x in RE_PCT.findall(s):
                if fv:
                    amt += float(x) / 100 * fv; found = True
        kind = "special" if "special" in low else ("interim" if "interim" in low else "final")
        if found and amt > 0:
            events.append(("dividend", round(amt, 6), kind))
        elif "%" in low or re.search(r"\brs|\bre\b", low):
            events.append(("dividend", None, f"unparsed:{kind}"))
    return events


def main():
    rows = []
    n_in = 0
    for f in sorted(glob.glob(f"{RAW}/*.json")):
        for r in json.load(open(f)):
            n_in += 1
            ex = r.get("exDate")
            if not ex or ex == "-":
                continue
            ex = pd.to_datetime(ex, format="%d-%b-%Y", errors="coerce")
            if pd.isna(ex):
                continue
            for typ, val, detail in parse(r.get("subject", ""), r.get("faceVal")):
                rows.append((r.get("isin"), r.get("symbol"), ex.date(), typ, val, detail, r.get("faceVal"),
                             r.get("series"), r.get("subject", "").strip()[:160]))
    df = pd.DataFrame(rows, columns=["isin", "symbol", "ex_date", "type", "factor_or_amount", "detail", "face_val",
                                     "series", "subject"])
    df["source"] = "nse-filing"
    obs_path = f"{REPO}/data/master/qa/observed_events.csv"
    if os.path.exists(obs_path):
        o = pd.read_csv(obs_path, parse_dates=["ex_date"])
        o = o[o["clean_ratio"].notna() | (o["factor"] < 0.6)]
        typ = np.where(o["factor"] > 1, "consolidation", "split")     # share-count event; bonus vs split is immaterial to the factor
        obs = pd.DataFrame({"isin": None, "symbol": o["symbol"], "ex_date": o["ex_date"].dt.date, "type": typ,
                            "factor_or_amount": o["clean_ratio"].fillna(o["factor"]), "detail": "observed:" + o["source"],
                            "face_val": None, "series": None, "subject": "", "source": o["source"]})
        df = pd.concat([df, obs], ignore_index=True)
    df = df.drop_duplicates(["isin", "ex_date", "type", "factor_or_amount", "detail"]).sort_values(["ex_date", "symbol"])
    df.to_csv(OUT, index=False)
    print(f"filings read: {n_in:,}  ->  price-relevant events: {len(df):,}")
    print(df.groupby("type").agg(n=("isin", "size"), unparsed=("factor_or_amount", lambda s: int(s.isna().sum())),
                                 first=("ex_date", "min"), last=("ex_date", "max")).to_string())
    print("\nunparsed dividend subjects, sample:")
    print(df[(df["type"] == "dividend") & df["factor_or_amount"].isna()]["subject"].drop_duplicates().head(8).to_string(index=False))


if __name__ == "__main__":
    main()
