"""First positioning-pattern pass on the engine's own data.

Data: option_minute_bars in prod Postgres — day-one live/replay bars
(with depth columns) + ~30d historical bars (OHLC/volume/OI only).
All real captured/official data; five weeks max — findings are
DIAGNOSTIC, not signal claims.

Questions:
  1. Does whole-book depth imbalance lead next-minute moves? (day-one
     bars only — the columns exist only where we recorded live)
  2. Expiry-day OI crush: when does the pin actually form intraday?
  3. ATM straddle premium vs realized across the backfilled weeks
  4. Spread behaviour: when is execution actually cheap/expensive?

Run: DATABASE_URL=<public> python analyze_positioning.py  (from kite-api/)
"""
import os
import sys

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

sys.path.insert(0, ".")

ENGINE = create_engine(os.environ["DATABASE_URL"])


def load(sql):
    return pd.read_sql(sql, ENGINE)


def q1_depth_imbalance():
    print("== Q1: depth imbalance (t) vs next-minute return (t+1) — day-one live bars ==")
    df = load("""
        select contract_id, kind, strike, minute, close, avg_depth_imbalance, tick_count
        from option_minute_bars
        where source='replay' and avg_depth_imbalance is not null
        order by contract_id, minute
    """)
    print(f"   {len(df)} bars with imbalance across {df.contract_id.nunique()} contracts")
    results = []
    for cid, g in df.groupby("contract_id"):
        if len(g) < 200:
            continue
        g = g.sort_values("minute")
        ret_next = g["close"].pct_change().shift(-1)
        imb = g["avg_depth_imbalance"]
        c = imb.corr(ret_next)
        if not np.isnan(c):
            results.append({"contract_id": cid, "kind": g.kind.iloc[0], "corr": c, "n": len(g)})
    r = pd.DataFrame(results)
    for kind, gg in r.groupby("kind"):
        print(f"   {kind}: mean corr {gg['corr'].mean():+.4f}  (median {gg['corr'].median():+.4f}, n contracts {len(gg)})")
    top = r.reindex(r["corr"].abs().sort_values(ascending=False).index).head(5)
    print("   strongest:", [(t.contract_id, round(t.corr, 3)) for t in top.itertuples()])

    # spot direction vs aggregate CE-vs-PE imbalance differential
    df["m"] = df["minute"]
    agg = df[df.kind.isin(["CE", "PE"])].pivot_table(index="m", columns="kind", values="avg_depth_imbalance", aggfunc="mean")
    spot = load("""
        select minute as m, close from option_minute_bars
        where source='replay' and contract_id='NIFTY_SPOT' order by minute
    """).set_index("m")["close"]
    both = agg.join(spot.rename("spot"), how="inner")
    both["diff"] = both["CE"] - both["PE"]
    both["spot_ret_next"] = both["spot"].pct_change().shift(-1)
    c = both["diff"].corr(both["spot_ret_next"])
    print(f"   aggregate (CE imb - PE imb) vs next-min spot return: corr {c:+.4f} (n={len(both.dropna())})")


def q2_expiry_oi_crush():
    print("\n== Q2: expiry-day intraday OI paths (2026-07-28, 24000 strike vs wings) ==")
    df = load("""
        select contract_id, strike, kind, minute, oi_close, close
        from option_minute_bars
        where source='replay' and kind in ('CE','PE') and expiry='2026-07-28'
        order by minute
    """)
    df["hour"] = pd.to_datetime(df["minute"], utc=True).dt.tz_convert("Asia/Kolkata").dt.floor("h")
    for label, strikes in [("ATM 24000", [24000.0]), ("wings ±300+", None)]:
        sub = df[df.strike.isin(strikes)] if strikes else df[(df.strike - 24000).abs() >= 300]
        oi = sub.groupby("hour")["oi_close"].mean()
        base = oi.iloc[0]
        path = " -> ".join(f"{v/base*100:.0f}%" for v in oi)
        print(f"   {label}: OI path vs 9am ({base/1e6:.1f}M base): {path}")


def q3_straddle_premium():
    print("\n== Q3: ATM straddle implied vs realized (backfilled weeks, 08-04 weekly) ==")
    df = load("""
        select contract_id, strike, kind, minute, close
        from option_minute_bars
        where expiry='2026-08-04' and kind in ('CE','PE')
        order by minute
    """)
    spot = load("""
        select minute, close from option_minute_bars
        where contract_id='NIFTY_SPOT' order by minute
    """)
    df["d"] = pd.to_datetime(df["minute"]).dt.date
    spot["d"] = pd.to_datetime(spot["minute"]).dt.date
    spot_close = spot.groupby("d")["close"].last()
    days = sorted(set(df["d"]))
    print("   date        spot     atm    straddle  implied-to-0804")
    for d in days[-10:]:
        sc = spot_close.get(d)
        if sc is None:
            continue
        day = df[df["d"] == d]
        eod = day.sort_values("minute").groupby(["strike", "kind"])["close"].last().unstack()
        if eod.empty or "CE" not in eod or "PE" not in eod:
            continue
        strikes = eod.index.values
        atm = strikes[np.abs(strikes - sc).argmin()]
        if pd.isna(eod.loc[atm, "CE"]) or pd.isna(eod.loc[atm, "PE"]):
            continue
        straddle = eod.loc[atm, "CE"] + eod.loc[atm, "PE"]
        print(f"   {d}  {sc:8.1f}  {atm:6.0f}  {straddle:7.1f}   {straddle/sc*100:5.2f}%")


def q4_spread_regimes():
    print("\n== Q4: when is execution cheap? avg spread by time-of-day (day-one, ATM±100) ==")
    df = load("""
        select minute, strike, kind, avg_spread, close
        from option_minute_bars
        where source='replay' and kind in ('CE','PE') and avg_spread is not null
          and abs(strike - 24000) <= 100
    """)
    ist = pd.to_datetime(df["minute"], utc=True).dt.tz_convert("Asia/Kolkata")
    df["bucket"] = pd.cut(
        ist.dt.hour * 60 + ist.dt.minute,
        bins=[555, 585, 630, 720, 810, 870, 900, 931],
        labels=["9:15-9:45", "9:45-10:30", "10:30-12:00", "12:00-13:30", "13:30-14:30", "14:30-15:00", "15:00-15:30"],
    )
    df["spread_bps_of_prem"] = df["avg_spread"] / df["close"].clip(lower=0.5) * 100
    out = df.groupby("bucket", observed=True).agg(
        abs_spread=("avg_spread", "mean"), pct_of_premium=("spread_bps_of_prem", "mean"), bars=("avg_spread", "size")
    )
    for b, row in out.iterrows():
        print(f"   {b:12} spread {row.abs_spread:.3f} pts  ({row.pct_of_premium:.2f}% of premium, n={int(row.bars)})")


if __name__ == "__main__":
    q1_depth_imbalance()
    q2_expiry_oi_crush()
    q3_straddle_premium()
    q4_spread_regimes()
