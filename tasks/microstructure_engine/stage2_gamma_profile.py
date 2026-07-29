"""Stage 2 readout — gamma by strike, aggregate gamma, concentration.

Measured quantities only (no dealer-sign assumptions — that is Stage 3):
gamma notional per 1% spot move, per strike:

    GEX_1pct(K) = sum over CE+PE at K of  gamma * OI_close * F^2 * 0.01

Zerodha OI is already in units (not lots), so no lot multiplier.
Reported in ₹ crore of delta-notional change per 1% move.

Run: DATABASE_URL=<public> python stage2_gamma_profile.py  (from kite-api/)
"""
import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, ".")
ENGINE = create_engine(os.environ["DATABASE_URL"])

CR = 1e7  # ₹ crore


def profile(day, expiry, times=("10:00", "13:00", "15:00")):
    print(f"\n=== {day} (near expiry {expiry}) ===")
    for hm in times:
        h, m = map(int, hm.split(":"))
        total_min = h * 60 + m - 330  # IST -> UTC
        utc_t = f"{total_min // 60:02d}:{total_min % 60:02d}:00"
        df = pd.read_sql(text("""
            select g.strike, g.kind, g.gamma, g.underlying, b.oi_close
            from option_greeks_minute g
            join option_minute_bars b
              on b.contract_id = g.contract_id and b.minute = g.minute
            where date(g.minute) = :d and g.expiry = :e
              and g.minute::time = :t and g.gamma is not null
        """), ENGINE, params={"d": day, "e": expiry, "t": utc_t})
        if df.empty:
            print(f"  {hm}: no rows")
            continue
        df["gex_cr"] = df.gamma * df.oi_close * df.underlying**2 * 0.01 / CR
        by_k = df.groupby("strike")["gex_cr"].sum().sort_index()
        total = by_k.sum()
        top = by_k.idxmax()
        conc = by_k.max() / total if total else float("nan")
        spot = df.underlying.iloc[0]
        top5 = by_k.sort_values(ascending=False).head(5)
        print(f"  {hm} IST | fwd {spot:.0f} | total gamma ₹{total:,.0f}cr/1% | "
              f"max-gamma strike {top:.0f} ({conc:.0%} of total)")
        print(f"        top strikes: " + ", ".join(f"{k:.0f}: ₹{v:,.0f}cr" for k, v in top5.items()))


if __name__ == "__main__":
    profile("2026-07-28", "2026-07-28")  # expiry pin day
    profile("2026-07-29", "2026-08-04")  # trend day
