"""Exploratory models on the backfilled minute+OI history.

Research probe. All numbers computed from real Zerodha historical candles
(minute_<date>_7d.parquet from backfill_history.py). Five sessions is a
descriptive sample — nothing here is a signal claim; the point is to see
which structures are worth tracking once the live engine accumulates data.

Sections:
  1. Daily OI put/call ratio (near expiry) vs next-session spot return
  2. Closing OI chain profile — where the walls sit vs spot
  3. ATM straddle at each close: implied next-move vs what realized
  4. Futures basis behaviour into expiry
  5. Intraday 30-min dOI vs dSpot (near expiry, both sides)
  6. Max pain by session vs spot close
"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")

PARQUET = sorted(Path("../data/options/history").glob("minute_*_7d.parquet"))[-1]


def load():
    df = pd.read_parquet(PARQUET)
    df["date"] = pd.to_datetime(df["date"])
    df["session"] = df["date"].dt.date
    return df


def session_closes(df):
    """Last minute row per contract per session."""
    return df.sort_values("date").groupby(["contract_id", "session"], as_index=False).last()


def main():
    df = load()
    spot = df[df.kind == "SPOT"]
    sessions = sorted(df.session.unique())
    spot_close = spot.groupby("session")["close"].last()
    near_exp = df[df.kind.isin(["CE", "PE"])]["expiry"].min()
    opts = df[(df.kind.isin(["CE", "PE"])) & (df.expiry == near_exp)]
    closes = session_closes(opts)

    print(f"data: {PARQUET.name} | sessions {sessions[0]}..{sessions[-1]} | near expiry {near_exp}")
    print(f"spot closes: {dict(spot_close.round(1))}")

    # 1. PCR vs next-session return
    print("\n== 1. near-expiry OI PCR at close vs next-session spot return ==")
    pcr = closes.pivot_table(index="session", columns="kind", values="oi", aggfunc="sum")
    pcr["pcr"] = pcr["PE"] / pcr["CE"]
    ret = spot_close.pct_change().shift(-1) * 100
    for s in sessions:
        nxt = f"{ret.get(s):+.2f}%" if pd.notna(ret.get(s)) else "  n/a"
        print(f"  {s}  PCR={pcr.loc[s,'pcr']:.3f}  next-session spot: {nxt}")

    # 2. OI walls on the final close
    print("\n== 2. closing OI chain profile (near expiry, last session) ==")
    last = closes[closes.session == sessions[-1]]
    prof = last.pivot_table(index="strike", columns="kind", values="oi", aggfunc="sum").fillna(0)
    top_ce = prof["CE"].nlargest(3)
    top_pe = prof["PE"].nlargest(3)
    s_last = spot_close.iloc[-1]
    print(f"  spot {s_last:.1f}")
    print("  call walls:", ", ".join(f"{int(k)} ({v/1e6:.1f}M)" for k, v in top_ce.items()))
    print("  put walls: ", ", ".join(f"{int(k)} ({v/1e6:.1f}M)" for k, v in top_pe.items()))

    # 3. ATM straddle implied vs realized
    print("\n== 3. ATM straddle at close: implied move to expiry vs next-session realized ==")
    for i, s in enumerate(sessions):
        sc = spot_close[s]
        day = closes[closes.session == s]
        strikes = day.strike.unique()
        atm = strikes[np.abs(strikes - sc).argmin()]
        ce = day[(day.strike == atm) & (day.kind == "CE")]["close"]
        pe = day[(day.strike == atm) & (day.kind == "PE")]["close"]
        if ce.empty or pe.empty:
            continue
        straddle = float(ce.iloc[0] + pe.iloc[0])
        implied_pct = straddle / sc * 100
        if i + 1 < len(sessions):
            nxt = sessions[i + 1]
            nxt_day_spot = spot[spot.session == nxt]
            realized = (nxt_day_spot.high.max() - nxt_day_spot.low.min()) / sc * 100
            realized_s = f"next-session range {realized:.2f}%"
        else:
            realized_s = "(expiry tomorrow)"
        print(f"  {s}  atm={int(atm)}  straddle={straddle:.1f}  implied-to-expiry {implied_pct:.2f}%  {realized_s}")

    # 4. futures basis by session
    print("\n== 4. near futures basis (close) ==")
    fut = df[df.kind == "FUT"]
    near_fut = fut[fut.expiry == fut.expiry.min()]
    fut_close = near_fut.groupby("session")["close"].last()
    for s in sessions:
        b = fut_close[s] - spot_close[s]
        print(f"  {s}  basis {b:+.1f} pts ({b / spot_close[s] * 1e4:+.1f} bps)")

    # 5. intraday 30-min dOI vs dSpot correlation
    print("\n== 5. 30-min dOI vs dSpot (near expiry) ==")
    spot_30 = spot.set_index("date")["close"].resample("30min").last().dropna()
    d_spot = spot_30.diff()
    for kind in ("CE", "PE"):
        oi_30 = (
            opts[opts.kind == kind]
            .groupby(pd.Grouper(key="date", freq="30min"))["oi"]
            .sum()
            .reindex(spot_30.index)
        )
        d_oi = oi_30.diff()
        both = pd.concat([d_spot, d_oi], axis=1, keys=["dspot", "doi"]).dropna()
        both = both[both.doi != 0]
        corr = both.dspot.corr(both.doi)
        print(f"  {kind}: corr(dSpot, dOI) = {corr:+.3f}  (n={len(both)})")

    # 6. max pain
    print("\n== 6. max pain (near expiry) by session ==")
    for s in sessions:
        day = closes[closes.session == s]
        p = day.pivot_table(index="strike", columns="kind", values="oi", aggfunc="sum").fillna(0)
        strikes = p.index.values
        pain = [
            ((np.maximum(k - strikes, 0) * p["PE"].values).sum()
             + (np.maximum(strikes - k, 0) * p["CE"].values).sum())
            for k in strikes
        ]
        mp = strikes[int(np.argmin(pain))]
        print(f"  {s}  max-pain {int(mp)}  (spot close {spot_close[s]:.1f}, gap {spot_close[s] - mp:+.1f})")


if __name__ == "__main__":
    main()
