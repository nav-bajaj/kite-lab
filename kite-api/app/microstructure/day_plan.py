"""Morning day-plan generator — the Judgment-layer prototype (ADVISORY).

    python -m app.microstructure.day_plan --date 2026-08-04 [--as-of 10:00]

Turns the measured morning state (regime read, IV percentile, gamma walls,
ATM credit) into a suggested structure + strikes + provisional risk band.
It is advisory and heuristic — it exists to build the CALL TRACK RECORD the
autonomy gates need, not to trigger trades. Every recommendation is
probabilistic and state-conditioned, never price-predictive (founder
principle, research/NOTE_risk_thresholds.md).

Structure:
- recommend_structure(...): the pure decision core (regime + IV percentile +
  credit thinness + expiry -> structure). No DB, no price prediction; this is
  where the founder principle lives and is exhaustively unit-tested.
- build_plan(conn, day, as_of): reconstructs the plan from stored state
  (gamma_profile_daily + bars + ledger) — for the retrospective track record,
  replay, and the EOD report. The live /admin path (beta_gtm_mvp) reuses
  recommend_structure directly on a compute_from_snapshot dict.

Risk numbers are quoted from the ACTUAL ledger distribution (with its n),
never fabricated. Until the day-type library is large (15-20+ sessions) and
the regime-at-MAE join is complete, the band is explicitly provisional.
"""
from __future__ import annotations

import argparse
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from app.microstructure.gamma_profile import (
    CONC_DIFFUSE, CONC_PIN, regime_from_concentration,
)

# Standing constraints every plan inherits — all measured, not assumed.
STANDING_CONSTRAINTS = [
    "Intraday-only: overnight/weekend carry is the dominant measured risk "
    "(-61.2 pt Fri->Mon counterfactual vs worst intraday MAE -78.3).",
    "No near-ATM transactions after 15:15 on expiry day (friction explodes "
    "as premium decays).",
    "Watch the spot-vs-parity divergence: the official close printed +150/+200 "
    "above the late tape on both new-timings days; anything settled off the "
    "15:20-15:30 tape inherits it.",
]


def recommend_structure(regime: str, iv_pctile: Optional[float], credit_thin: bool,
                        is_expiry: bool, max_gamma_strike: Optional[float]) -> dict:
    """Pure decision core. Encodes the 6-session observations as a structure
    selection conditioned on regime + IV percentile + credit thinness. Returns
    a structure, a center strike hint, rationale, and caveats. No price
    prediction — the regime state carries the call."""
    caveats: list[str] = []
    ivp = None if iv_pctile is None else round(iv_pctile, 2)

    if regime == "PIN-GRAVITY":
        if is_expiry and credit_thin:
            structure = "IRON_FLY"
            rationale = ("Pin regime but thin expiry credit — the exact setup of "
                         "the ledger's only loss (Aug-04: credit 93, MAE -78.3, "
                         "final -55.2). Defined-risk wings convert the open-ended "
                         "gap/whipsaw tail into fixed risk while keeping pin theta.")
            caveats.append("Do NOT sell the naked straddle here; credit does not "
                           "pay for the two-sided tail (n=2 expiries, 1 pin 1 breaker).")
        else:
            structure = "SHORT_STRADDLE"
            rationale = ("Concentrated gamma at a wall — long-gamma-like, "
                         "mean-reverting (Jul-28 archetype: conc 36%->57%, spot "
                         "magnetized, vol crushed). Sell realized-vs-implied at the "
                         "max-gamma strike; profit is back-loaded, MAE hits early.")
            caveats.append("Iron-fly is the defined-risk alternative if IV is low "
                           "(wings cheapest at IV lows).")
        center = max_gamma_strike

    elif regime == "DIFFUSE":
        center = max_gamma_strike
        if ivp is not None and ivp >= 0.7:
            structure = "DEFINED_RISK_SHORT"
            rationale = ("Diffuse/trend-capable but IV rich (pctile "
                         f"{ivp:.0%}) — premium is worth selling only with wings on. "
                         "Wide iron-fly or reduced size; naked short premium is "
                         "wrong when moves extend (max-gamma migrates with spot).")
        else:
            structure = "DIRECTIONAL_DEBIT_SPREAD"
            rationale = ("Diffuse, covering-fuel drift (near-call OI drains, writers "
                         "re-form a rung up — 4/4 up-drift days closed strong). A "
                         "debit spread with the drift aligns theta+direction with "
                         "defined risk; or stand aside. Naked short straddle "
                         "discouraged — this is the regime that extends.")
            caveats.append("HYPOTHESIS ONLY: all diffuse days so far were UP-drift "
                           "(n=3); zero down-diffuse tested. Do not assume symmetry.")
        caveats.append("If STAND_ASIDE is the honest call on the day, take it — the "
                       "track record values a correct pass.")

    elif regime == "MIXED":
        structure = "REDUCED_SIZE"
        center = max_gamma_strike
        rationale = ("Regime unresolved (concentration between the diffuse and pin "
                     "cutoffs) — the Aug-03 midday MIXED read was transient and "
                     "resolved back to diffuse. Half size or wait for the read to "
                     "firm before committing structure.")

    else:  # UNKNOWN
        structure = "STAND_ASIDE"
        center = None
        rationale = "No regime read available (missing gamma profile). No plan."

    caveats.append(f"Concentration cutoffs {CONC_DIFFUSE:g}/{CONC_PIN:g} are "
                   "HEURISTIC and uncalibrated; the read is probabilistic.")
    return {
        "structure": structure,
        "center_strike": center,
        "iv_pctile": ivp,
        "rationale": rationale,
        "caveats": caveats,
    }


def iv_percentile(conn, day: str, atm_iv: Optional[float], snap="10:00") -> tuple:
    """Percentile of today's ATM IV within the stored history (gamma_profile_daily).
    Returns (pctile in [0,1] or None, n prior days)."""
    if atm_iv is None:
        return None, 0
    hist = pd.read_sql(text("""
        select atm_iv from gamma_profile_daily
        where snap_time=:s and session_date < :d and atm_iv is not null
    """), conn, params={"s": snap, "d": day})
    vals = hist.atm_iv.dropna().to_numpy(float)
    if len(vals) < 3:
        return None, int(len(vals))
    return float((vals < atm_iv).mean()), int(len(vals))


def _atm_straddle(conn, day: str, as_of: str) -> Optional[float]:
    """ATM straddle price (near expiry) at as_of, from bars. IST filtering is
    done in pandas (portable across sqlite/Postgres), matching daily_report."""
    df = pd.read_sql(text("""
        select minute, strike, kind, close from option_minute_bars
        where date(minute)=:d and kind in ('CE','PE')
          and expiry=(select min(expiry) from option_minute_bars where date(minute)=:d and kind in ('CE','PE'))
    """), conn, params={"d": day})
    spot = pd.read_sql(text("""
        select minute, close from option_minute_bars
        where contract_id='NIFTY_SPOT' and date(minute)=:d
    """), conn, params={"d": day})
    if df.empty or spot.empty:
        return None
    for x in (df, spot):
        x["hm"] = pd.to_datetime(x.minute, utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")
    df, spot = df[df.hm == as_of], spot[spot.hm == as_of]
    if df.empty or spot.empty:
        return None
    piv = df.pivot_table(index="strike", columns="kind", values="close", aggfunc="first").dropna()
    if piv.empty:
        return None
    s0 = float(spot.close.iloc[0])
    atm_k = piv.index[np.abs(piv.index - s0).argmin()]
    return float(piv.loc[atm_k].sum())


def ledger_credit_stats(conn) -> dict:
    """Historical entry-credit + MAE distribution from the paper ledger, joined
    to the day's regime (gamma_profile_daily @10:00) where available. The basis
    for 'thin credit' — quoted with n, never a fabricated threshold."""
    led = pd.read_sql(text("""
        select l.session_date, l.entry_credit, l.final_pnl, l.mae, l.underwater_minutes,
               g.concentration
        from paper_straddle_ledger l
        left join gamma_profile_daily g
          on g.session_date=l.session_date and g.snap_time='10:00'
    """), conn)
    if led.empty:
        return {"n": 0}
    led["regime"] = led.concentration.apply(regime_from_concentration)
    wins = led[led.final_pnl > 0]
    return {
        "n": int(len(led)),
        "credit_p25": float(led.entry_credit.quantile(0.25)),
        "credit_min_win": float(wins.entry_credit.min()) if not wins.empty else None,
        "mae_min": float(led.mae.min()),
        "mae_median": float(led.mae.median()),
        "by_regime": {
            r: {"n": int(len(g)), "mae_min": float(g.mae.min()),
                "mae_median": float(g.mae.median())}
            for r, g in led.groupby("regime") if r != "UNKNOWN"
        },
    }


def build_plan(conn, day: str, as_of: str = "10:00") -> Optional[dict]:
    """Reconstruct the morning plan from stored state at as_of."""
    prof = pd.read_sql(text("""
        select expiry, forward, max_gamma_strike, concentration, atm_iv
        from gamma_profile_daily where session_date=:d and snap_time=:s
    """), conn, params={"d": day, "s": as_of})
    if prof.empty:
        return None
    p = prof.iloc[0]
    regime = regime_from_concentration(p.concentration)
    is_expiry = pd.notna(p.expiry) and str(pd.to_datetime(p.expiry).date()) == day
    ivp, iv_n = iv_percentile(conn, day, p.atm_iv, snap=as_of)
    credit = _atm_straddle(conn, day, as_of)
    cstats = ledger_credit_stats(conn)

    # Thin credit = below the ledger's winning-day credits (cited, not invented).
    thin_ref = cstats.get("credit_min_win")
    credit_thin = bool(credit is not None and thin_ref is not None and credit < thin_ref)

    rec = recommend_structure(regime, ivp, credit_thin, is_expiry, p.max_gamma_strike)
    return {
        "day": day, "as_of": as_of, "regime": regime,
        "concentration": None if pd.isna(p.concentration) else float(p.concentration),
        "forward": None if pd.isna(p.forward) else float(p.forward),
        "max_gamma_strike": None if pd.isna(p.max_gamma_strike) else float(p.max_gamma_strike),
        "atm_iv": None if pd.isna(p.atm_iv) else float(p.atm_iv),
        "iv_pctile": rec["iv_pctile"], "iv_pctile_n": iv_n,
        "is_expiry": bool(is_expiry),
        "atm_credit": None if credit is None else round(credit, 1),
        "credit_thin": credit_thin,
        "ledger": cstats,
        "recommendation": rec,
    }


def render_plan(plan: Optional[dict]) -> list:
    out = ["## Morning day-plan (ADVISORY — heuristic, probabilistic, not a trigger)"]
    if not plan:
        out.append("- no stored morning state (gamma_profile_daily row missing)")
        return out
    rec = plan["recommendation"]
    conc = plan["concentration"]
    out.append(f"- As of {plan['as_of']}: regime **{plan['regime']}**"
               + (f" (conc {conc:.0%})" if conc is not None else "")
               + (f", forward {plan['forward']:.0f}" if plan.get("forward") else "")
               + (", EXPIRY DAY" if plan["is_expiry"] else ""))
    ivp = plan["iv_pctile"]
    iv_line = f"- ATM IV {plan['atm_iv'] * 100:.2f}%" if plan.get("atm_iv") else "- ATM IV n/a"
    if ivp is not None:
        iv_line += f" | IV percentile {ivp:.0%} (n={plan['iv_pctile_n']} prior days)"
    out.append(iv_line)
    if plan["atm_credit"] is not None:
        tag = " — THIN vs winning-day credits" if plan["credit_thin"] else ""
        out.append(f"- ATM straddle credit {plan['atm_credit']:.0f} pts{tag}")
    out.append(f"- **Structure: {rec['structure']}**"
               + (f" centered {rec['center_strike']:.0f}" if rec["center_strike"] else ""))
    out.append(f"  - {rec['rationale']}")
    led = plan["ledger"]
    if led.get("n"):
        band = f"MAE band (all): min {led['mae_min']:+.1f}, median {led['mae_median']:+.1f} (n={led['n']})"
        reg = led.get("by_regime", {}).get(plan["regime"])
        if reg:
            band += f" | {plan['regime']}: min {reg['mae_min']:+.1f}, median {reg['mae_median']:+.1f} (n={reg['n']})"
        out.append(f"  - Provisional risk band from the ledger — {band}. "
                   "Not yet calibrated; conditioning firms at 15-20+ sessions.")
    for c in rec["caveats"]:
        out.append(f"  - caveat: {c}")
    out.append("- Standing constraints:")
    out.extend(f"  - {c}" for c in STANDING_CONSTRAINTS)
    return out


def generate(day: str, as_of: str = "10:00", database_url: Optional[str] = None) -> str:
    from app.microstructure.materialize import _resolve_url

    engine = create_engine(_resolve_url(database_url))
    try:
        with engine.connect() as conn:
            plan = build_plan(conn, day, as_of)
        return "\n".join([f"# Options day-plan — {day}", ""] + render_plan(plan))
    finally:
        engine.dispose()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--as-of", default="10:00")
    args = ap.parse_args()
    print(generate(args.date, args.as_of))


if __name__ == "__main__":
    main()
