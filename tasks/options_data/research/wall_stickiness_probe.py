"""PRE-REGISTERED test: does an anchored gamma wall pull price toward it?

Thesis (2026-08-18): a growing gamma pile only pins price if the pile is
STANDING STILL. A pile that grows while moving is trend confirmation, not
a pin — which would explain why the concentration slope tested flat in
RESULTS_2026-08-18_gamma_positioning.md Q3: it averages two opposite
mechanisms together.

    state   (09:20-13:00): beta of wall on spot. ~0 anchored, ~1 tracking
    outcome (13:00-15:15): does spot move toward where the wall WAS at 13:00
    split: median beta.  control: morning range (quiet-day confound)
    FALSIFIED IF: convergence is the same in both buckets.

Registered before the data was looked at, run once. Result: FALSIFIED
(Welch t=0.68, corr(beta, converge)=-0.09). See the RESULTS doc §Q5 —
including the confound that makes it worse than merely insignificant.

Run:  railway run --service Postgres -- python wall_stickiness_probe.py
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

STATE_START, STATE_END = "09:20", "13:00"
OUTCOME_END = "15:15"


def wall_beta(wall, spot) -> Optional[float]:
    """How far the wall moves per unit of spot movement.

    ~0 = anchored while price runs at it (the pin candidate); ~1 = the wall
    is just tracking the money, which is near-mechanical because gamma peaks
    at ATM and carries no information. Regression, not endpoint difference:
    strikes are quantised to a 50-pt grid, so endpoints are far too lumpy.
    """
    w, s = np.asarray(wall, float), np.asarray(spot, float)
    if len(w) < 2 or len(w) != len(s) or np.var(s) < 1e-9:
        return None
    # ddof must match: np.cov defaults to ddof=1, np.var to ddof=0, and
    # mixing them scales beta by n/(n-1).
    return float(np.cov(w, s)[0, 1] / np.var(s, ddof=1))


def convergence(spot_at_decision: float, spot_at_end: float,
                wall_at_decision: float) -> float:
    """Did spot move toward where the wall was at the decision point?

    The wall reference is FIXED at the decision minute on purpose. Measuring
    against the wall's own later position would let a wall that chases price
    register as convergence — which is the exact opposite of the claim being
    tested (price pulled to structure, not structure dragged to price).
    """
    return abs(spot_at_decision - wall_at_decision) - abs(spot_at_end - wall_at_decision)


def build_panel(m: pd.DataFrame) -> pd.DataFrame:
    """m: per-minute d, hm, wall, conc, spot, exp -> one row per session."""
    rows = []
    for d, grp in m.groupby("d"):
        grp = grp.sort_values("hm")
        am = grp[(grp.hm >= STATE_START) & (grp.hm <= STATE_END)]
        pm = grp[(grp.hm >= STATE_END) & (grp.hm <= OUTCOME_END)]
        if len(am) < 60 or len(pm) < 30:
            continue
        beta = wall_beta(am.wall, am.spot)
        if beta is None:
            continue
        rows.append(dict(
            d=d, expiry=(d == grp.exp.iloc[0]), beta=beta,
            am_range=float(am.spot.max() - am.spot.min()),
            conc13=float(pm.conc.iloc[0]),
            gap13=abs(float(pm.spot.iloc[0]) - float(pm.wall.iloc[0])),
            converge=convergence(float(pm.spot.iloc[0]), float(pm.spot.iloc[-1]),
                                 float(pm.wall.iloc[0]))))
    return pd.DataFrame(rows)


def report(df: pd.DataFrame) -> None:
    pd.set_option("display.width", 250, "display.max_columns", 40)
    med = df.beta.median()
    df = df.assign(bucket=np.where(df.beta <= med, "sticky", "tracking"))
    print(f"=== sessions {len(df)} (expiries {df.expiry.sum()}) | median beta {med:.3f} ===")
    print(df.groupby("bucket")[["converge", "gap13", "am_range", "beta"]]
          .agg(["count", "mean", "median"]).to_string())
    a, b = df[df.bucket == "sticky"].converge, df[df.bucket == "tracking"].converge
    diff = a.mean() - b.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    print(f"\nPREDICTION sticky > tracking: diff {diff:+.2f} pts, Welch t {diff / se:+.2f} -> "
          f"{'SUPPORTED' if diff / se > 2 else 'NOT SUPPORTED'}")
    print(f"corr(beta, converge) = {df.beta.corr(df.converge):+.3f}")
    print(f"\nCONTROL quiet-day: corr(beta, morning range) = {df.beta.corr(df.am_range):+.3f}")
    print("\nCONFOUND — how far the wall sits from spot in each bucket:")
    print(df.groupby("bucket")["gap13"].agg(["mean", "median"]).to_string())
    print("\nexpiry days (pin mechanism strongest):")
    print(df[df.expiry][["d", "beta", "conc13", "gap13", "converge"]]
          .to_string(index=False, float_format=lambda x: f"{x:8.2f}"))


def main():
    from sqlalchemy import create_engine, text

    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ["DATABASE_URL"]
    engine = create_engine(url.replace("postgresql://", "postgresql+psycopg2://", 1))
    try:
        with engine.connect() as conn:
            g = pd.read_sql(text("""select session_date::text d, minute,
                                           max_gamma_strike wall, concentration conc,
                                           expiry::text exp
                                    from gamma_profile_minute order by 1,2"""), conn)
            s = pd.read_sql(text("""select date(minute)::text d, minute, close spot
                                    from option_minute_bars
                                    where contract_id='NIFTY_SPOT' order by minute"""), conn)
    finally:
        engine.dispose()
    for x in (g, s):
        x["hm"] = pd.to_datetime(x.minute, utc=True).dt.tz_convert(
            "Asia/Kolkata").dt.strftime("%H:%M")
    report(build_panel(g.merge(s[["d", "hm", "spot"]], on=["d", "hm"], how="inner")))


if __name__ == "__main__":
    main()
