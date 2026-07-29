"""Short-straddle simulation on the two captured days — real minute bars,
real bid/ask (entries at bid, exits at ask; no mid-price fantasy).

Day 1 (2026-07-28, replay): expiry pin day — the regime short straddles
want. Day 2 (2026-07-29, live): gap + trend day — the regime that hurts.

Variants:
  A. naive: sell ATM straddle 09:20, hold, buy back 15:15
  B. rolling: same entry; whenever |spot - K| >= ROLL_AT points, buy back
     both legs (ask) and re-sell the new ATM (bid). Max 3 rolls.

Also computes, for day 2, when the OI-drain early warning (overrun call
strikes losing >10% of 9am OI) fired relative to the straddle drawdown.

Two days — this is a mechanics/feasibility study, not a backtest.
"""
import os
import sys

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, ".")
ENGINE = create_engine(os.environ["DATABASE_URL"])

ENTRY_T, EXIT_T = "09:20", "15:15"
ROLL_AT = 100
MAX_ROLLS = 3
LOT = 75


def load_day(day, source, expiry):
    q = """
      select minute, kind, strike, close, bid_close, ask_close, oi_close
      from option_minute_bars
      where source=:src and expiry=:exp and kind in ('CE','PE')
      order by minute
    """
    df = pd.read_sql(text(q), ENGINE, params={"src": source, "exp": expiry})
    spot = pd.read_sql(text("""
      select minute, close from option_minute_bars
      where source=:src and contract_id='NIFTY_SPOT' order by minute
    """), ENGINE, params={"src": source})
    for d in (df, spot):
        d["ist"] = pd.to_datetime(d["minute"], utc=True).dt.tz_convert("Asia/Kolkata")
        d["hm"] = d["ist"].dt.strftime("%H:%M")
    return df, spot


def quotes_at(df, hm):
    """{(strike, kind): (close, bid, ask)} for one minute."""
    m = df[df.hm == hm]
    return {(r.strike, r.kind): (r.close, r.bid_close, r.ask_close) for r in m.itertuples()}


def nearest_strike(df, spot_px):
    ks = np.array(sorted(df.strike.unique()))
    return float(ks[np.abs(ks - spot_px).argmin()])


def sell_straddle(q, k):
    ce, pe = q.get((k, "CE")), q.get((k, "PE"))
    if not ce or not pe or not ce[1] or not pe[1]:
        return None
    return ce[1] + pe[1]  # sell at bid


def buy_straddle(q, k):
    ce, pe = q.get((k, "CE")), q.get((k, "PE"))
    if not ce or not pe or not ce[2] or not pe[2]:
        return None
    return ce[2] + pe[2]  # buy at ask


def mtm(q, k):
    ce, pe = q.get((k, "CE")), q.get((k, "PE"))
    if not ce or not pe:
        return None
    return ce[0] + pe[0]


def run_day(label, source, expiry):
    df, spot = load_day(label, source, expiry)
    spot_by_hm = dict(zip(spot.hm, spot.close))
    minutes = [hm for hm in spot.hm if ENTRY_T <= hm <= EXIT_T]

    s0 = spot_by_hm[ENTRY_T]
    k0 = nearest_strike(df, s0)
    entry_credit = sell_straddle(quotes_at(df, ENTRY_T), k0)

    # Variant A: hold
    a_path, worst_a = [], 0.0
    for hm in minutes:
        v = mtm(quotes_at(df, hm), k0)
        if v is not None:
            pnl = entry_credit - v
            a_path.append((hm, pnl))
            worst_a = min(worst_a, pnl)
    exit_cost = buy_straddle(quotes_at(df, EXIT_T), k0)
    a_final = entry_credit - exit_cost

    # Variant B: roll on drift
    credit = entry_credit
    k, rolls, worst_b = k0, 0, 0.0
    roll_log = []
    for hm in minutes:
        q = quotes_at(df, hm)
        s = spot_by_hm.get(hm)
        v = mtm(q, k)
        if v is not None:
            pnl = credit - v
            worst_b = min(worst_b, pnl)
        if s and abs(s - k) >= ROLL_AT and rolls < MAX_ROLLS and hm < EXIT_T:
            cost = buy_straddle(q, k)
            nk = nearest_strike(df, s)
            recredit = sell_straddle(q, nk)
            if cost and recredit:
                credit = credit - cost + recredit
                roll_log.append(f"{hm}: {k:.0f}->{nk:.0f} (buyback {cost:.1f}, resell {recredit:.1f})")
                k, rolls = nk, rolls + 1
    b_exit = buy_straddle(quotes_at(df, EXIT_T), k)
    b_final = credit - b_exit

    print(f"\n=== {label} — {source} — expiry {expiry} ===")
    print(f"  entry {ENTRY_T}: spot {s0:.1f}, ATM {k0:.0f}, credit {entry_credit:.1f} pts (sold at bid)")
    print(f"  A HOLD : exit {EXIT_T} at ask -> P&L {a_final:+.1f} pts (₹{a_final*LOT:+,.0f}/lot) | worst intraday {worst_a:+.1f}")
    print(f"  B ROLL@{ROLL_AT}: rolls={rolls} -> P&L {b_final:+.1f} pts (₹{b_final*LOT:+,.0f}/lot) | worst intraday {worst_b:+.1f}")
    for r in roll_log:
        print(f"      roll {r}")
    return a_path


def oi_warning_day2():
    print("\n=== Day-2 OI-drain early warning vs straddle drawdown ===")
    df = pd.read_sql(text("""
      select minute, strike, oi_close from option_minute_bars
      where source='live' and expiry='2026-08-04' and kind='CE' and strike in (24000, 24100)
      order by minute
    """), ENGINE)
    df["hm"] = pd.to_datetime(df["minute"], utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")
    base = df[df.hm <= "09:30"].groupby("strike")["oi_close"].last()
    fired = None
    for hm, g in df[df.hm > "09:30"].groupby("hm"):
        cur = g.set_index("strike")["oi_close"]
        drains = [(cur[k] / base[k] - 1) for k in base.index if k in cur]
        if drains and all(d < -0.10 for d in drains):
            fired = hm
            break
    print(f"  both overrun call strikes (24000/24100) >10% below 9:30 OI at: {fired or 'never'}")


if __name__ == "__main__":
    run_day("2026-07-28 (expiry pin day)", "replay", "2026-07-28")
    run_day("2026-07-29 (trend day)", "live", "2026-08-04")
    oi_warning_day2()
