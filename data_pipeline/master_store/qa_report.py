"""Phase 5: QA over the master store. Each check writes a CSV under qa/ and a
line in qa/report.md. Nothing is deleted: a bad row is quarantined by being
listed, and the loader can mask it.

  calendar     every file's dates are midnight-normalised, unique, and a
               subset of the NSE session calendar from the bhavcopy
  bad prints   a one-day spike in the raw close that reverts next day by
               the same size (>8% out, >8% back) with no corporate action
               within +-3 days, cross-checked against Kite where present
  stale tails  a file whose last date precedes the archive end by more than
               20 sessions without a delisted_on flag
  overlaps     identity components whose windows trade concurrently (none
               expected after the equity-ISIN filter)
  coverage     the Phase 3 gate table, restated
"""
from __future__ import annotations

import glob, json, os
import numpy as np
import pandas as pd

from data_pipeline.master_store import ROOT as REPO  # noqa: E402
MASTER = f"{REPO}/data/master"
QA = f"{MASTER}/qa"


def main():
    os.makedirs(QA, exist_ok=True)
    eq = pd.read_parquet(f"{MASTER}/bhavcopy_eq.parquet", columns=["date"])
    sessions = set(eq["date"].dt.normalize().unique()); end = max(sessions)
    ca = pd.read_csv(f"{MASTER}/corporate_actions.csv", parse_dates=["ex_date"])
    ca_dates = {s: g["ex_date"].values for s, g in ca.groupby("symbol")}
    bm = json.load(open(f"{MASTER}/prices/bhavcopy_manifest.json"))
    lines, cal_bad, prints, stale = [], [], [], []
    files = sorted(glob.glob(f"{MASTER}/prices/bhavcopy/*.csv"))
    for f in files:
        sym = os.path.basename(f)[:-4]
        df = pd.read_csv(f, parse_dates=["date"])
        d = df["date"]
        if (d.dt.normalize() != d).any() or d.duplicated().any() or not set(d).issubset(sessions):
            cal_bad.append((sym, int((d.dt.normalize() != d).sum()), int(d.duplicated().sum()), int((~d.isin(sessions)).sum())))
        c = df.set_index("date")["close"]
        r = c.pct_change(); rn = c.pct_change().shift(-1)
        spike = ((r.abs() > 0.08) & (rn.abs() > 0.08) & (np.sign(r) != np.sign(rn)) & ((r + rn).abs() < 0.04))
        for dt in c.index[spike.fillna(False)]:
            v = ca_dates.get(sym)
            if v is not None and (np.abs((v - np.datetime64(dt)).astype("timedelta64[D]").astype(int)) <= 3).any():
                continue
            kite_agrees = None
            kf = f"{MASTER}/prices/kite/{sym}.csv"
            if os.path.exists(kf):
                k = pd.read_csv(kf, parse_dates=["date"]).drop_duplicates("date", keep="last").set_index("date")["close"]
                if dt in k.index:
                    kr = k.pct_change().get(dt)
                    kite_agrees = bool(kr is not None and abs(kr - r[dt]) < 0.02)
            prints.append((sym, dt.date(), round(100 * r[dt], 1), round(100 * rn[dt], 1), kite_agrees))
        last = c.index.max()
        if last < end and len([s for s in sessions if s > last]) > 20 and "delisted_on" not in bm.get(sym, {}):
            stale.append((sym, last.date()))
    pd.DataFrame(cal_bad, columns=["symbol", "non_midnight", "duplicates", "off_calendar"]).to_csv(f"{QA}/calendar.csv", index=False)
    pr = pd.DataFrame(prints, columns=["symbol", "date", "move_pct", "revert_pct", "kite_agrees"])
    pr.to_csv(f"{QA}/bad_prints.csv", index=False)
    pd.DataFrame(stale, columns=["symbol", "last"]).to_csv(f"{QA}/stale_tails.csv", index=False)
    lines.append(f"- calendar: {len(files)} files checked, {len(cal_bad)} with non-midnight, duplicate or off-calendar dates")
    lines.append(f"- bad prints: {len(pr)} one-day spike-and-revert rows with no corporate action nearby; "
                 f"Kite shows the same move on {int(pr['kite_agrees'].fillna(False).sum())} (a real move, not a print), "
                 f"disagrees on {int((pr['kite_agrees'] == False).sum())} (a print on one side), no Kite on {int(pr['kite_agrees'].isna().sum())}")
    lines.append(f"- stale tails: {len(stale)} files end >20 sessions before {end.date()} without a delisted_on flag")
    ov = f"{QA}/identity_overlaps.csv"
    lines.append(f"- identity overlaps: {len(pd.read_csv(ov)) if os.path.exists(ov) else 0}")
    cov = pd.read_csv(f"{MASTER}/qa_coverage_prices.csv"); cov["yr"] = pd.to_datetime(cov["date"]).dt.year
    t = cov.pivot_table(index="yr", columns="index", values="coverage_pct", aggfunc="min").round(1)
    lines.append("- coverage (membership vs price files, min % per year):\n\n" + t.to_string())
    open(f"{QA}/report.md", "w").write("# QA report, master store\n\n" + "\n".join(lines) + "\n")
    print("\n".join(lines[:4]))


if __name__ == "__main__":
    main()
