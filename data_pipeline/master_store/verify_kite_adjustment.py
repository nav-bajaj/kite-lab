"""Measure Kite's adjustment convention against NSE's filings.

For each symbol with both a Kite series (adjusted) and a bhavcopy series
(raw, what traded), the ratio kite_close / raw_close is piecewise constant:
flat between events, stepping on an ex-date. Every step is matched to the
corporate-actions table and the observed step is compared to the factor the
event implies:

  bonus A:B         B/(A+B)
  split X->Y        Y/X
  dividend D        (P_cum - D) / P_cum      P_cum = raw close on the last cum day
  rights A:B @ P    ((B * P_cum) + A * (face + P)) / ((A + B) * P_cum)
  demerger          no prediction; the observed step is recorded as the factor

A step with no event within +-3 trading days is an unexplained
discontinuity — a bad print on one side, or a filing NSE never published —
and goes to the QA log. Output: qa/kite_vs_filings.csv and a summary by type.
"""
from __future__ import annotations

import glob, os
import numpy as np
import pandas as pd

from data_pipeline.master_store import ROOT as REPO, MASTER  # noqa: E402
MASTER = MASTER
KITE = f"{MASTER}/prices/kite"
QA = f"{MASTER}/qa"


def main(tol_step=0.004, max_symbols=None):
    os.makedirs(QA, exist_ok=True)
    eq = pd.read_parquet(f"{MASTER}/bhavcopy_eq.parquet", columns=["date", "symbol", "series", "close"])
    eq = eq[eq["close"] > 0]
    eq["pri"] = eq["series"].map({"EQ": 0, "BE": 1, "BZ": 2}).fillna(3)
    eq = eq.sort_values(["symbol", "date", "pri"]).drop_duplicates(["symbol", "date"])
    ca = pd.read_csv(f"{MASTER}/corporate_actions.csv", parse_dates=["ex_date"])
    ca_by_sym = {s: g.sort_values("ex_date") for s, g in ca.groupby("symbol")}
    files = sorted(glob.glob(f"{KITE}/*.csv"))
    if max_symbols:
        files = files[:max_symbols]
    rows, unexplained = [], []
    for f in files:
        sym = os.path.basename(f)[:-4]
        k = pd.read_csv(f, parse_dates=["date"]).set_index("date")["close"]
        r = eq[eq["symbol"] == sym].drop_duplicates("date").set_index("date")["close"].sort_index()
        j = pd.concat([k.rename("k"), r.rename("r")], axis=1, join="inner")
        j = j[(j["k"] > 0) & (j["r"] > 0)]
        if len(j) < 60:
            continue
        ratio = (j["k"] / j["r"])
        # persistent step: five-day median after vs five-day median before
        before = ratio.rolling(5).median().shift(1)
        after = ratio[::-1].rolling(5).median()[::-1]
        step = (after / before).dropna()
        tick = (2 * 0.05 / j["r"]).reindex(step.index)          # rounding to 0.05 on either feed
        cand = step[((step - 1).abs() > np.maximum(tol_step, tick))]
        # keep the first day of each run of consecutive flagged days
        ev = cand[~(cand.index.to_series().diff() <= pd.Timedelta(days=4)).fillna(False).values] if len(cand) else cand
        ev = 1.0 / ev                                              # -> the factor Kite applied to history
        cas = ca_by_sym.get(sym, pd.DataFrame())
        for d, sfac in ev.items():
            cum_day = j.index[j.index.get_loc(d) - 1]
            p_cum = j.loc[cum_day, "r"]
            match = cas[(cas["ex_date"] >= d - pd.Timedelta(days=4)) & (cas["ex_date"] <= d + pd.Timedelta(days=4))] if len(cas) else cas
            if match.empty:
                unexplained.append((sym, d.date(), round(sfac, 5), p_cum)); continue
            # predicted combined factor from all matched events
            pred = 1.0; types = []
            for e in match.itertuples():
                types.append(e.type)
                if e.type in ("bonus", "split", "consolidation") and pd.notna(e.factor_or_amount):
                    pred *= float(e.factor_or_amount)
                elif e.type == "dividend" and pd.notna(e.factor_or_amount):
                    pred *= (p_cum - float(e.factor_or_amount)) / p_cum
                elif e.type == "rights":
                    a, b, prem = None, None, None
                    try:
                        ab, pr = str(e.detail).split("@prem=")
                        a, b = [int(x) for x in ab.split(":")]; prem = None if pr == "None" else float(pr)
                    except Exception:  # noqa: BLE001
                        pass
                    if a and b and prem is not None:
                        fv = float(str(e.face_val).replace(",", "") or 0) if pd.notna(e.face_val) else 0.0
                        pred *= (b * p_cum + a * (fv + prem)) / ((a + b) * p_cum)
                    else:
                        pred = np.nan
                elif e.type == "demerger":
                    pred = np.nan
            rows.append((sym, d.date(), "+".join(sorted(set(types))), round(sfac, 5), round(pred, 5) if pd.notna(pred) else None, p_cum))
    df = pd.DataFrame(rows, columns=["symbol", "ex_date", "types", "observed", "predicted", "p_cum"])
    df["err_pct"] = (df["observed"] / df["predicted"] - 1).abs() * 100
    df.to_csv(f"{QA}/kite_vs_filings.csv", index=False)
    un = pd.DataFrame(unexplained, columns=["symbol", "date", "step", "p_cum"])
    un.to_csv(f"{QA}/kite_steps_unexplained.csv", index=False)
    print(f"symbols compared: {len(files)}   matched steps: {len(df):,}   unexplained steps: {len(un):,}")
    summ = df.dropna(subset=["predicted"]).groupby("types").agg(
        n=("observed", "size"), median_err_pct=("err_pct", "median"), p90_err_pct=("err_pct", lambda s: s.quantile(0.9)),
        within_0p2=("err_pct", lambda s: round(100 * (s <= 0.2).mean(), 1)))
    print(summ.sort_values("n", ascending=False).head(12).to_string())
    prints = int(((ratio / ratio.shift(1) - 1).abs() > 0.02).sum()) if len(files) == 1 else None
    dm = df[df["types"].str.contains("demerger")]
    print(f"\ndemerger steps observed (Kite adjusts them): {len(dm)}; e.g. {dm[['symbol','ex_date','observed']].head(5).values.tolist()}")


if __name__ == "__main__":
    import sys
    main(max_symbols=int(sys.argv[1]) if len(sys.argv) > 1 else None)
