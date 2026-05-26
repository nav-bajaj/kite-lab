"""Phase 1 EDA — does any of our signal universe predict forward Nifty returns?

Computes information coefficient (IC) = Spearman rank correlation between each
signal at time t-1 and the Nifty 50 forward return over horizons {1, 5, 20, 60}
trading days. Separated IS (2010-2018) vs OOS (2019-2026) — if signals only
"work" in-sample, that's a flag for cherry-picking. Negative IC is fine (and
expected for some signals like VIX); we care about |IC| being persistent.

Decision rule for Phase 2:
  - At least 2-3 signals with |IC| ≥ 0.05 in BOTH IS and OOS, and IS/OOS
    sign-consistent. This is a low bar but a real filter.
  - If nothing clears it, the breadth-driven directional thesis is weak and
    we should reconsider the approach before building a strategy.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
# Manual Spearman: rank-and-Pearson (avoids scipy dependency)
def spearmanr(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    xr = x.rank()
    yr = y.rank()
    return float(xr.corr(yr)), float("nan")

from breadth_signals import build_or_load as load_breadth
from macro_signals import build_or_load as load_macro

INDICES_DIR = Path("/Users/navdeep/Documents/stock_data/indices_data_full")

IS_START = pd.Timestamp("2010-01-04")
IS_END = pd.Timestamp("2018-12-31")
OOS_START = pd.Timestamp("2019-01-01")
OOS_END = pd.Timestamp("2026-05-12")


def load_nifty() -> pd.Series:
    df = pd.read_csv(INDICES_DIR / "NIFTY_50.csv", parse_dates=["date"])
    return df.set_index("date")["close"].sort_index()


def main() -> None:
    breadth = load_breadth()
    macro = load_macro()
    nifty = load_nifty()

    # Align everything onto the breadth index (NSE 500 trading days)
    signals = pd.concat([breadth, macro], axis=1)
    signals = signals.reindex(nifty.index).ffill()

    # Forward returns of Nifty
    forward_horizons = [1, 5, 20, 60]
    fwd = pd.DataFrame({h: nifty.pct_change(h, fill_method=None).shift(-h)
                         for h in forward_horizons}, index=nifty.index)

    # Signals at t are knowable EOD t; predict returns from close[t] to close[t+h].
    # That's already what shift(-h) does — fwd[h] at index t IS return from t to t+h.

    # Drop signals that don't have enough OOS observations
    keep_cols = [c for c in signals.columns
                 if signals[c].loc[OOS_START:OOS_END].notna().sum() > 200]
    signals = signals[keep_cols]

    print(f"Phase 1 EDA — IC of signals vs Nifty forward returns\n")
    print(f"  IS:  {IS_START.date()} → {IS_END.date()}")
    print(f"  OOS: {OOS_START.date()} → {OOS_END.date()}\n")

    rows = []
    for sig in signals.columns:
        s = signals[sig]
        row = {"signal": sig}
        for label, sd, ed in [("IS", IS_START, IS_END), ("OOS", OOS_START, OOS_END)]:
            mask = (s.index >= sd) & (s.index <= ed)
            for h in forward_horizons:
                a = s[mask]
                b = fwd[h][mask]
                pair = pd.concat([a, b], axis=1).dropna()
                if len(pair) < 50:
                    row[f"{label}_h{h}"] = np.nan
                    continue
                ic, _ = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
                row[f"{label}_h{h}"] = float(ic)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("signal")
    # Reorder columns: pair IS/OOS by horizon
    col_order = []
    for h in forward_horizons:
        col_order += [f"IS_h{h}", f"OOS_h{h}"]
    df = df[col_order]

    # Print formatted
    print(df.round(4).to_string())
    print()
    print("Sign-consistency check (sign(IS_h5) == sign(OOS_h5)?):")
    for sig in df.index:
        is_ic = df.loc[sig, "IS_h5"]
        oos_ic = df.loc[sig, "OOS_h5"]
        consistent = (np.sign(is_ic) == np.sign(oos_ic)) and abs(oos_ic) >= 0.02
        flag = "✓" if consistent and abs(oos_ic) >= 0.05 else (" " if consistent else "✗")
        print(f"  {flag}  {sig:<28} IS_h5={is_ic:+.3f}  OOS_h5={oos_ic:+.3f}  "
              f"{'PASS' if consistent and abs(oos_ic) >= 0.05 else ('weak' if consistent else 'INCONSISTENT')}")

    print(f"\nDecision: signals with |OOS_h5| ≥ 0.05 and sign-consistent across IS/OOS "
          f"are the candidates for Phase 2.")


if __name__ == "__main__":
    main()
