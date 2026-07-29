"""Day-2 (2026-07-29, gap + trend day) vs day-1 (expiry pin day).

First out-of-sample pass on the day-one hypotheses plus trend-day OI
mechanics. Two days of depth data — still diagnostic.

Run: DATABASE_URL=<public> python analyze_day2_trend.py  (from kite-api/)
"""
import os
import sys

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, ".")
ENGINE = create_engine(os.environ["DATABASE_URL"])


def load(sql, **params):
    return pd.read_sql(text(sql), ENGINE, params=params)


def q1_imbalance_oos():
    print("== A. Imbalance vs next-minute return — out-of-sample day 2 (trend day) ==")
    df = load("""
        select contract_id, kind, strike, minute, close, avg_depth_imbalance
        from option_minute_bars
        where source='live' and avg_depth_imbalance is not null
        order by contract_id, minute
    """)
    res = []
    for cid, g in df.groupby("contract_id"):
        if len(g) < 200:
            continue
        g = g.sort_values("minute")
        c = g["avg_depth_imbalance"].corr(g["close"].pct_change().shift(-1))
        if not np.isnan(c):
            res.append({"cid": cid, "kind": g.kind.iloc[0], "strike": g.strike.iloc[0], "corr": c})
    r = pd.DataFrame(res)
    for kind, gg in r.groupby("kind"):
        print(f"   {kind}: mean {gg['corr'].mean():+.4f}  median {gg['corr'].median():+.4f}  n={len(gg)}")
    # day-1's cluster was ITM puts (strikes >= spot+250). Same zone today: spot ~24150-24250
    itm_puts = r[(r.kind == "PE") & (r.strike >= 24400)]
    print(f"   ITM-put zone today (PE, K>=24400): mean {itm_puts['corr'].mean():+.4f} "
          f"median {itm_puts['corr'].median():+.4f} n={len(itm_puts)}")
    strongest = r.reindex(r["corr"].abs().sort_values(ascending=False).index).head(5)
    print("   strongest:", [(t.cid, round(t.corr, 3)) for t in strongest.itertuples()])


def q2_trend_day_oi():
    print("\n== B. Trend-day OI mechanics: strikes the rally ran through (08-04 CE) ==")
    df = load("""
        select strike, kind, minute, oi_close, close
        from option_minute_bars
        where source='live' and expiry='2026-08-04' and kind='CE'
          and strike in (24000, 24100, 24200, 24300, 24400)
        order by minute
    """)
    df["hour"] = pd.to_datetime(df["minute"], utc=True).dt.tz_convert("Asia/Kolkata").dt.floor("h")
    piv = df.pivot_table(index="hour", columns="strike", values="oi_close", aggfunc="last")
    base = piv.iloc[0]
    print("   CE OI vs 9am base (spot path: 24142 open -> ~24225 mid -> close):")
    for h, row in piv.iterrows():
        cells = "  ".join(f"{int(k)}:{row[k]/base[k]*100:5.0f}%" for k in piv.columns if not pd.isna(row[k]) and base[k])
        print(f"   {h.strftime('%H:%M')}  {cells}")


def q3_spread_curve_compare():
    print("\n== C. Spread curve: trend day vs expiry day (ATM±100 of each day's center) ==")
    for label, src, center in [("expiry day (07-28)", "replay", 24000), ("trend day (07-29)", "live", 24200)]:
        df = load("""
            select minute, avg_spread, close from option_minute_bars
            where source=:src and kind in ('CE','PE') and avg_spread is not null
              and abs(strike - :center) <= 100
        """, src=src, center=center)
        ist = pd.to_datetime(df["minute"], utc=True).dt.tz_convert("Asia/Kolkata")
        df["bucket"] = pd.cut(ist.dt.hour * 60 + ist.dt.minute, bins=[555, 630, 810, 870, 931],
                              labels=["open-10:30", "10:30-13:30", "13:30-14:30", "14:30-close"])
        df["pct"] = df["avg_spread"] / df["close"].clip(lower=0.5) * 100
        out = df.groupby("bucket", observed=True).agg(spread=("avg_spread", "mean"), pct=("pct", "mean"))
        cells = "  ".join(f"{b}: {r.spread:.2f}pts/{r.pct:.2f}%" for b, r in out.iterrows())
        print(f"   {label}: {cells}")


def q4_widened_strike_quality():
    print("\n== D. Widened strikes: partial-day coverage by design ==")
    df = load("""
        select contract_id, min(minute) as first_bar, count(*) as bars
        from option_minute_bars
        where source='live' and strike >= 24500 and kind in ('CE','PE') and expiry='2026-08-04'
        group by contract_id order by first_bar limit 6
    """)
    for t in df.itertuples():
        first = pd.to_datetime(t.first_bar, utc=True).tz_convert("Asia/Kolkata").strftime("%H:%M")
        print(f"   {t.contract_id}: first bar {first} IST, {t.bars} bars")


def q5_straddle_update():
    print("\n== E. Straddle ledger update (08-04 expiry) ==")
    df = load("""
        select minute, strike, kind, close from option_minute_bars
        where expiry='2026-08-04' and kind in ('CE','PE')
          and minute >= '2026-07-29 09:15:00+05:30'
        order by minute
    """)
    spot = load("""
        select minute, close from option_minute_bars
        where contract_id='NIFTY_SPOT' and source='live' order by minute
    """)
    sc = spot["close"].iloc[-1]
    eod = df.sort_values("minute").groupby(["strike", "kind"])["close"].last().unstack()
    atm = eod.index.values[np.abs(eod.index.values - sc).argmin()]
    straddle = eod.loc[atm, "CE"] + eod.loc[atm, "PE"]
    print(f"   2026-07-29 close: spot {sc:.1f}, ATM {atm:.0f}, straddle {straddle:.1f} "
          f"= {straddle/sc*100:.2f}% implied to 08-04")
    print(f"   context: 07-28 close implied 1.25%+... and today spot MOVED {24211-23988:+d}ish pts intraday —")
    print("   realized is landing; ledger closes when 08-04 expires.")


if __name__ == "__main__":
    q1_imbalance_oos()
    q2_trend_day_oi()
    q3_spread_curve_compare()
    q4_widened_strike_quality()
    q5_straddle_update()
