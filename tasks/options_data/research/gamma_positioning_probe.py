"""Does the gamma profile help POSITION a trade? (2026-08-18, ledger n=15)

Tests three candidate uses of the Stage-2 gamma profile against the paper
straddle ledger:

  1. strike selection  — center the straddle on the max-gamma strike
     instead of ATM (variants B vs C, same entry time, only K differs);
  2. overnight strike  — center on the PRIOR session's closing wall (D);
  3. hold/size         — condition the afternoon on the morning
     concentration SLOPE (10:00 -> 13:00), scoring only P&L earned
     after 13:00 so the test stays ex-ante.

Run:  railway run --service Postgres -- python gamma_positioning_probe.py
      (reads DATABASE_PUBLIC_URL, falling back to DATABASE_URL)

The scoring rule matters. A short straddle's exit is what a live trader
would pay, so entry fills at the BID and exit at the ASK; marks in between
use closes. Conditioning variables must be readable at or before the
decision they inform — the 15:15 concentration cannot judge a trade that
exits at 15:15, which is the trap the first pass of this probe fell into
(it produced corr=0.47 where the honest number is 0.10).

Findings: RESULTS_2026-08-18_gamma_positioning.md.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

ENTRY_T, EXIT_T, MID_T = "09:20", "15:15", "13:00"
SLOPE_BAND = 0.01   # |dconc| below this reads as flat, not a direction


def pick_nearest_strike(strikes, target: float) -> float:
    """The traded strike closest to `target` — how any of these variants
    turns a price level into something you can actually sell."""
    ks = np.sort(np.asarray(strikes, dtype=float))
    if not len(ks):
        raise ValueError("no strikes")
    return float(ks[np.abs(ks - float(target)).argmin()])


def simulate_straddle(bars: pd.DataFrame, strike: float,
                      entry_t: str = ENTRY_T, exit_t: str = EXIT_T) -> Optional[dict]:
    """Sell the `strike` straddle at entry_t, buy it back at exit_t.

    `bars` needs columns hm, kind (CE/PE), strike, close, bid_close,
    ask_close. Credit is taken at the bid and the exit paid at the ask —
    the ledger's convention, so variants stay comparable to it. Returns
    None when either leg is missing at either end rather than guessing a
    fill: an unfillable variant must not score as a flat day.
    """
    sub = bars[bars.strike == strike]
    if sub.empty:
        return None

    def leg(t, kind, col):
        m = sub[(sub.hm == t) & (sub.kind == kind)]
        return float(m[col].iloc[0]) if len(m) and pd.notna(m[col].iloc[0]) else None

    entry_legs = [leg(entry_t, k, "bid_close") for k in ("CE", "PE")]
    exit_legs = [leg(exit_t, k, "ask_close") for k in ("CE", "PE")]
    if None in entry_legs or None in exit_legs:
        return None

    credit = sum(entry_legs)
    piv = sub.pivot_table(index="hm", columns="kind", values="close", aggfunc="first").dropna()
    piv = piv[(piv.index >= entry_t) & (piv.index <= exit_t)]
    if piv.empty or "CE" not in piv.columns or "PE" not in piv.columns:
        return None

    path = credit - (piv.CE + piv.PE)
    return {
        "strike": strike,
        "credit": credit,
        "path": path,
        "final": credit - sum(exit_legs),
        "mae": float(path.min()),
        "mae_t": str(path.idxmin()),
    }


def split_at(path: pd.Series, t: str = MID_T) -> Optional[dict]:
    """Split a P&L path at `t` into what was already earned and what came
    after — the only way to score an afternoon decision without paying
    itself the morning's profit."""
    before, after = path[path.index <= t], path[path.index >= t]
    if before.empty or after.empty:
        return None
    at_t = float(before.iloc[-1])
    return {
        "at_t": at_t,
        "pnl_after": float(after.iloc[-1]) - at_t,
        "mae_after": float(after.min()) - at_t,
    }


def bucket_slope(dconc: Optional[float], band: float = SLOPE_BAND) -> str:
    """Concentration slope -> regime-change label. The dead band keeps
    sampling noise from being read as a direction."""
    if dconc is None or not np.isfinite(dconc):
        return "unknown"
    if dconc >= band:
        return "building"
    if dconc <= -band:
        return "decaying"
    return "flat"


# ---------------------------------------------------------------- driver

def _load(conn):
    from sqlalchemy import text

    def ist(s):
        return pd.to_datetime(s, utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")

    prof = pd.read_sql(text("""
        select session_date::text d, snap_time, max_gamma_strike mk, concentration conc
        from gamma_profile_daily order by 1, 2"""), conn)
    days = sorted(prof.d.unique())
    bars, spot = {}, {}
    for d in days:
        b = pd.read_sql(text("""
            select minute, kind, strike, close, bid_close, ask_close
            from option_minute_bars where date(minute)=:d and kind in ('CE','PE')
              and expiry=(select min(expiry) from option_minute_bars
                          where date(minute)=:d and kind in ('CE','PE'))"""),
            conn, params={"d": d})
        s = pd.read_sql(text("""
            select minute, close from option_minute_bars
            where contract_id='NIFTY_SPOT' and date(minute)=:d order by minute"""),
            conn, params={"d": d})
        b["hm"], s["hm"] = ist(b.minute), ist(s.minute)
        bars[d], spot[d] = b, s
    return prof.pivot(index="d", columns="snap_time"), days, bars, spot


def run(conn) -> pd.DataFrame:
    P, days, bars, spot = _load(conn)

    def spot_at(d, t):
        m = spot[d][spot[d].hm == t]
        return float(m.close.iloc[0]) if len(m) else None

    rows = []
    for i, d in enumerate(days):
        try:
            mk10, c10, c13, c15 = (P[("mk", "10:00")][d], P[("conc", "10:00")][d],
                                   P[("conc", "13:00")][d], P[("conc", "15:15")][d])
        except KeyError:
            continue
        s920, s1000 = spot_at(d, ENTRY_T), spot_at(d, "10:00")
        if s920 is None or s1000 is None:
            continue
        prev_mk = P[("mk", "15:15")][days[i - 1]] if i else None
        ks = bars[d].strike.unique()

        prev_off = None
        variants = {
            "A": (pick_nearest_strike(ks, s920), ENTRY_T),    # ledger baseline
            "B": (pick_nearest_strike(ks, s1000), "10:00"),   # ATM, later entry
            "C": (pick_nearest_strike(ks, mk10), "10:00"),    # centered on the wall
        }
        if prev_mk is not None:
            prev_k = pick_nearest_strike(ks, prev_mk)
            variants["D"] = (prev_k, ENTRY_T)
            prev_off = prev_k - pick_nearest_strike(ks, s920)

        r = {"d": d, "c10": c10, "c13": c13, "dc_am": c13 - c10, "dc_full": c15 - c10,
             "walloff": pick_nearest_strike(ks, mk10) - pick_nearest_strike(ks, s1000),
             "spotmove": (spot_at(d, EXIT_T) or np.nan) - s920}
        r["prev_walloff"] = prev_off
        for nm, (K, t0) in variants.items():
            sim = simulate_straddle(bars[d], K, t0)
            r[f"{nm}_pnl"] = None if sim is None else round(sim["final"], 2)
            r[f"{nm}_mae"] = None if sim is None else round(sim["mae"], 2)
            if nm == "A" and sim:
                sp = split_at(sim["path"])
                if sp:
                    r.update(A_at13=round(sp["at_t"], 2),
                             A_pnl_pm=round(sp["pnl_after"], 2),
                             A_mae_pm=round(sp["mae_after"], 2))
        r["bucket"] = bucket_slope(r["dc_am"])
        rows.append(r)
    return pd.DataFrame(rows)


def report(df: pd.DataFrame) -> None:
    pd.set_option("display.width", 260, "display.max_columns", 60)
    print("=== panel (n=%d sessions with a gamma profile) ===" % len(df))
    print(df[["d", "c10", "c13", "dc_am", "bucket", "walloff",
              "A_pnl", "B_pnl", "C_pnl", "D_pnl"]]
          .to_string(index=False, float_format=lambda x: f"{x:7.2f}"))

    print("\n=== Q1 POSITIONING: wall-centered vs ATM-centered ===")
    for nm, lbl in (("A", "A 09:20 @ ATM  (ledger baseline)"),
                    ("B", "B 10:00 @ ATM  (entry-time control)"),
                    ("C", "C 10:00 @ WALL (gamma-positioned)"),
                    ("D", "D 09:20 @ prior-close WALL")):
        s, m = df[f"{nm}_pnl"].dropna(), df[f"{nm}_mae"].dropna()
        print(f"  {lbl}: n={len(s):2d} total {s.sum():+7.1f} mean {s.mean():+6.2f} "
              f"median {s.median():+6.2f} W/L {(s > 0).sum()}/{(s <= 0).sum()} "
              f"worst MAE {m.min():+7.2f}")
    bc = df.dropna(subset=["B_pnl", "C_pnl"])
    print(f"  paired B vs C (only K differs), n={len(bc)}: wall wins "
          f"{(bc.C_pnl > bc.B_pnl).sum()}/{len(bc)}, mean diff "
          f"{(bc.C_pnl - bc.B_pnl).mean():+.2f}")

    print("\n=== Q2 Is D's edge gamma, or moneyness x direction? ===")
    dd = df.dropna(subset=["A_pnl", "D_pnl"]).copy()
    dd["diff"] = dd.D_pnl - dd.A_pnl
    dd["dir_term"] = dd.prev_walloff * dd.spotmove
    print(f"  head-to-head: D {(dd['diff'] > 0).sum()} / A {(dd['diff'] < 0).sum()} "
          f"/ tie {(dd['diff'] == 0).sum()}")
    print(f"  corr(D-A, prior-wall offset x spot move) = "
          f"{dd['diff'].corr(dd.dir_term):+.3f}   <- near 1.0 means the 'edge' is "
          "a bet on direction relative to a stale strike, not a gamma effect")

    print("\n=== Q3 EX-ANTE: morning conc slope -> the afternoon ===")
    h = df.dropna(subset=["A_pnl_pm"])
    print(h.groupby("bucket")[["A_pnl_pm", "A_mae_pm"]]
          .agg(["count", "mean", "median", "min"]).to_string())
    print(f"\n  corr(slope, P&L after 13:00) = {h.dc_am.corr(h.A_pnl_pm):+.3f}  <- return: nothing")
    print(f"  corr(conc LEVEL at 13:00, P&L after 13:00) = {h.c13.corr(h.A_pnl_pm):+.3f}")
    b = h[h.bucket == "building"].A_mae_pm
    o = h[h.bucket != "building"].A_mae_pm
    print(f"  worst afternoon drawdown: building {b.min():+.2f} vs not-building "
          f"{o.min():+.2f} — the buckets must SEPARATE for the slope to be a "
          "risk conditioner; at n=15 they do not.")


def main():
    from sqlalchemy import create_engine

    # DATABASE_PUBLIC_URL first: the laptop path is `railway run --service
    # Postgres`, which injects BOTH, and the internal host does not resolve
    # off-platform.
    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ["DATABASE_URL"]
    engine = create_engine(url.replace("postgresql://", "postgresql+psycopg2://", 1))
    try:
        with engine.connect() as conn:
            report(run(conn))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
