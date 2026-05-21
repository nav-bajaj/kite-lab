"""Stitch OOS-B + OOS-C equity curves for each candidate and report
performance on 2021-01-01 -> 2026-05-08. Uses existing run outputs;
no re-runs needed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

RUNS = ROOT / "tasks/om25_alt/runs"

VARIANTS = {
    "L6_NSE500":      RUNS / "om25d_20260521_185025",
    "OM25_Nifty250":  RUNS / "om25d_20260521_185025",
    "OM25_NSE500":    RUNS / "om25d_20260521_185025",
    "ROM25_NSE500":   RUNS / "20260521_175705",
    "LV25_NSE500":    RUNS / "lv25_20260521_180846",
    "MV25_NSE500":    RUNS / "mv25_20260521_183120",
    "MV25d_NSE500":   RUNS / "om25d_20260521_185025",
    "OM25d_NSE500":   RUNS / "om25d_20260521_185025",
    "OM25d_Nifty250": RUNS / "om25d_20260521_185025",
}

START = pd.Timestamp("2021-01-01")
END   = pd.Timestamp("2026-05-08")


def load_equity(path: Path) -> pd.Series:
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    return df["pv"].astype(float)


def stitch(oosb: pd.Series, oosc: pd.Series) -> pd.Series:
    """Clip OOS-B to >= START, then rebase OOS-C to continue from OOS-B's last value."""
    b = oosb.loc[oosb.index >= START]
    if len(b) == 0:
        return oosc.loc[oosc.index >= START]
    last_b = b.iloc[-1]
    c = oosc.copy()
    if len(c) == 0:
        return b
    c = c * (last_b / c.iloc[0])
    # Drop any OOS-C dates that overlap with OOS-B
    c = c.loc[c.index > b.index[-1]]
    return pd.concat([b, c])


def metrics(pv: pd.Series) -> dict:
    if len(pv) < 2:
        return {}
    pv = pv.loc[(pv.index >= START) & (pv.index <= END)]
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    dd = (pv / pv.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd < 0 else np.nan
    total_ret = pv.iloc[-1] / pv.iloc[0] - 1
    return {
        "start": str(pv.index[0].date()),
        "end": str(pv.index[-1].date()),
        "years": round(years, 2),
        "total_return_pct": round(total_ret * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(sharpe, 3),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(dd * 100, 2),
        "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None,
    }


def main():
    rows = []
    for variant, src in VARIANTS.items():
        oosb_path = src / f"OOS-B_{variant}_equity.csv"
        oosc_path = src / f"OOS-C_{variant}_equity.csv"
        if not oosb_path.exists() or not oosc_path.exists():
            print(f"[skip] {variant} — missing equity files")
            continue
        oosb = load_equity(oosb_path)
        oosc = load_equity(oosc_path)
        stitched = stitch(oosb, oosc)
        m = metrics(stitched)
        rows.append({"variant": variant, **m})

    df = pd.DataFrame(rows)
    df = df.sort_values("sharpe", ascending=False).reset_index(drop=True)
    print(f"=== Performance 2021-01-01 -> 2026-05-08 (stitched OOS-B late + OOS-C) ===\n")
    print(df.to_string(index=False))
    out = ROOT / "tasks/om25_alt/runs" / "candidates_2021plus.csv"
    df.to_csv(out, index=False)
    print(f"\n[wrote] {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
