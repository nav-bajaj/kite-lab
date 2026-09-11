"""Corporate actions NSE's filings feed does not carry, read off prices.

The filings API is incomplete for splits and bonuses (JSW Steel's 2017 split
is filed as "Fv Splt Frm Rs 10 To Re 1"; KRBL's 2011 split and LGB's 2010
split are not filed at all). Two observational sources fill the gap, both
tagged so nothing observed is ever mistaken for a filing:

  kite-observed     for companies Kite serves: a persistent step in
                    kite_close / raw_close (five-day medians either side)
                    with no filing of a share-count type within +-5 days.
                    Kite's factor is exact; accepted when it is within 1% of
                    a clean ratio, or below 0.6 (a large split/bonus/demerger
                    Kite chose to adjust).
  bhavcopy-observed for companies Kite does not serve: an overnight move in
                    the raw close within 0.5% of a clean ratio and larger
                    than 30%, with no filing within +-5 days. A crash can
                    land near 0.5; the tolerance is tight and every row is
                    listed in qa/observed_events.csv for review.

Clean ratios: bonus A:B for A,B <= 10 -> B/(A+B); splits 10->5,2,1; 5->2,1;
2->1; and their inverses (consolidation).
"""
from __future__ import annotations

import glob, os
import numpy as np
import pandas as pd

from data_pipeline.master_store import ROOT as REPO  # noqa: E402
MASTER = f"{REPO}/data/master"

CLEAN = sorted({b / (a + b) for a in range(1, 11) for b in range(1, 11)} | {0.5, 0.2, 0.1, 0.4, 0.25})
CLEAN = sorted(set(CLEAN) | {1 / x for x in CLEAN if x > 0})


def nearest_clean(f: float):
    c = min(CLEAN, key=lambda x: abs(x - f))
    return c, abs(f / c - 1)


def main():
    ca = pd.read_csv(f"{MASTER}/corporate_actions.csv", parse_dates=["ex_date"])
    if "source" in ca.columns:
        ca = ca[ca["source"] == "nse-filing"]          # never let a previous run's observations mask themselves
    share = ca[ca["type"].isin(["split", "bonus", "consolidation", "rights", "demerger"])]
    filed = {s: g["ex_date"].values for s, g in share.groupby("symbol")}
    divs = {s: g[["ex_date", "factor_or_amount"]].dropna().values for s, g in ca[ca["type"] == "dividend"].groupby("symbol")}
    def dividend_explains(sym, d, fct, p_cum):
        """Kite adjusts some recent dividends; a step that matches (P-D)/P for a
        filed dividend within +-5 days is that, not a bonus."""
        v = divs.get(sym)
        if v is None or not p_cum:
            return False
        for ex, amt in v:
            if abs((pd.Timestamp(ex) - pd.Timestamp(d)).days) <= 5:
                if abs(fct / ((p_cum - float(amt)) / p_cum) - 1) <= 0.01:
                    return True
        return False
    def has_filing(sym, d):
        v = filed.get(sym)
        return v is not None and (np.abs((v - np.datetime64(d)).astype("timedelta64[D]").astype(int)) <= 5).any()

    rows = []
    kite_syms = {os.path.basename(f)[:-4] for f in glob.glob(f"{MASTER}/prices/kite/*.csv")}
    for f in sorted(glob.glob(f"{MASTER}/prices/bhavcopy/*.csv")):
        sym = os.path.basename(f)[:-4]
        raw = pd.read_csv(f, parse_dates=["date"]).drop_duplicates("date").set_index("date")["close"]
        raw = raw[raw > 0]
        if sym in kite_syms:
            k = pd.read_csv(f"{MASTER}/prices/kite/{sym}.csv", parse_dates=["date"]).drop_duplicates("date", keep="last").set_index("date")["close"]
            j = pd.concat([k.rename("k"), raw.rename("r")], axis=1, join="inner")
            j = j[(j["k"] > 0) & (j["r"] > 0)]
            if len(j) < 30:
                continue
            ratio = j["k"] / j["r"]
            before = ratio.rolling(5).median().shift(1); after = ratio[::-1].rolling(5).median()[::-1]
            step = (after / before).dropna()
            tick = (2 * 0.05 / j["r"]).reindex(step.index)
            cand = step[((step - 1).abs() > np.maximum(0.03, tick))]
            # a run of flagged days brackets one event; the ex-date is the day with
            # the largest single-day change in the ratio inside that run
            daily = (ratio / ratio.shift(1) - 1).abs()
            keep = {}
            if len(cand):
                run_id = (cand.index.to_series().diff() > pd.Timedelta(days=6)).cumsum()
                for _, g in cand.groupby(run_id.values):
                    # positional window: a suspension can put the jump many calendar
                    # days after the flagged run but only one trading row later
                    p0 = max(0, daily.index.get_loc(g.index.min()) - 2)
                    p1 = min(len(daily) - 1, daily.index.get_loc(g.index.max()) + 6)
                    win = daily.iloc[p0:p1 + 1]
                    if win.empty:
                        continue
                    d = win.idxmax(); keep[d] = float(g.iloc[0])
            for d, s in keep.items():
                fct = 1.0 / s                                    # factor Kite applied to history
                if has_filing(sym, d):
                    continue
                i = j.index.get_loc(d); p_cum = float(j["r"].iloc[i - 1]) if i > 0 else None
                if dividend_explains(sym, d, fct, p_cum):
                    continue
                c, err = nearest_clean(fct)
                # plausibility: a share-count event is a clean ratio; a "consolidation"
                # of x1.1 is Kite reversing a dividend adjustment, not an event
                if fct > 1 and (fct < 1.5 or err > 0.003):
                    continue
                if 0.85 < fct < 1 and err > 0.003:
                    continue
                if err <= 0.01 or fct < 0.6:
                    rows.append((sym, d.date(), "kite-observed", round(fct, 6), c if err <= 0.01 else None, round(err, 4)))
        else:
            mv = (raw / raw.shift(1)).dropna()
            cand = mv[(mv < 0.7) | (mv > 1.4)]
            for d, s in cand.items():
                if has_filing(sym, d):
                    continue
                c, err = nearest_clean(s)
                if err <= 0.005:
                    rows.append((sym, d.date(), "bhavcopy-observed", round(s, 6), c, round(err, 4)))
    df = pd.DataFrame(rows, columns=["symbol", "ex_date", "source", "factor", "clean_ratio", "err"])
    # one event detected twice across a rename gap: same symbol, same ratio, within 25 days
    df["ex_date"] = pd.to_datetime(df["ex_date"])
    df = df.sort_values(["symbol", "ex_date"])
    dup = (df["symbol"] == df["symbol"].shift()) & (df["clean_ratio"] == df["clean_ratio"].shift()) & \
          ((df["ex_date"] - df["ex_date"].shift()).dt.days <= 25)
    df = df[~dup]
    df["ex_date"] = df["ex_date"].dt.date
    df.to_csv(f"{MASTER}/qa/observed_events.csv", index=False)
    print(df.groupby("source").agg(n=("symbol", "size"), symbols=("symbol", "nunique")).to_string())
    print("factor distribution (kite-observed):", df[df.source == "kite-observed"]["clean_ratio"].value_counts().head(8).to_dict())


if __name__ == "__main__":
    main()
