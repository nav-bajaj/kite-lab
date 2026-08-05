"""Stage 2 — gamma profile, in two speeds.

- compute_from_snapshot(): LIVE — takes the worker's 10-second chain
  snapshot (option_chain_snapshots payload) and derives parity forward,
  ATM IV, gamma-by-strike GEX, total, max-gamma strike, concentration
  and the heuristic regime read. Pure math on the snapshot + no history.
- store_daily(): EOD — persists 10:00/13:00/15:15 profile rows from
  bars+greeks into gamma_profile_daily for the day-type library.

Measured quantities only; dealer-sign assumptions are Stage 3.
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import (
    Column, Date, DateTime, Float, MetaData, String, Table, create_engine, text,
)

from app.microstructure.greeks import greeks_b76, implied_vol_b76, t_years

log = logging.getLogger(__name__)

RISK_FREE = 0.065
CR = 1e7

# Spot vs parity-forward gap beyond which we flag a dislocation. Near-expiry
# carry is a few points; 40 sits well above it and below the ~150-200 pt
# close-print events. Heuristic, uncalibrated — widens the day-type library.
DIVERGENCE_FLAG_PTS = 40.0

# Gamma-concentration regime cutoffs (max-gamma strike's share of total).
# Single-sourced so the daily report and day-plan generator agree with the
# live read. Heuristic, uncalibrated — thresholds firm up as the library grows.
CONC_PIN = 0.35       # >= this -> PIN-GRAVITY (long-gamma-like, mean-reverting)
CONC_DIFFUSE = 0.25   # <  this -> DIFFUSE (short-gamma-like, trend-capable)


def regime_from_concentration(conc: Optional[float]) -> str:
    if conc is None:
        return "UNKNOWN"
    if conc > CONC_PIN:
        return "PIN-GRAVITY"
    if conc < CONC_DIFFUSE:
        return "DIFFUSE"
    return "MIXED"

_metadata = MetaData()

gamma_profile_daily = Table(
    "gamma_profile_daily",
    _metadata,
    Column("session_date", Date, primary_key=True),
    Column("snap_time", String(5), primary_key=True),
    Column("expiry", Date),
    Column("forward", Float),
    Column("total_gex_cr", Float),
    Column("max_gamma_strike", Float),
    Column("concentration", Float),
    Column("atm_iv", Float),
    Column("computed_at", DateTime(timezone=True)),
)


def compute_from_snapshot(payload: dict, now_ist: datetime) -> Optional[dict]:
    """payload = option_chain_snapshots JSON (spot + contracts dict)."""
    contracts = payload.get("contracts") or {}
    rows = [
        {"cid": cid, **c}
        for cid, c in contracts.items()
        if c.get("kind") in ("CE", "PE") and c.get("ltp") and c.get("expiry")
    ]
    if not rows:
        return None
    df = pd.DataFrame(rows)
    near = min(df.expiry)
    df = df[df.expiry == near].copy()
    expiry_d = date.fromisoformat(near)
    T = t_years(now_ist, expiry_d)
    if T <= 0 or df.empty:
        return None

    # parity forward from the snapshot chain itself
    piv = df.pivot_table(index="strike", columns="kind", values="ltp", aggfunc="first").dropna()
    if len(piv) < 3:
        return None
    F = float((piv.index + (piv.CE - piv.PE) * math.exp(RISK_FREE * T)).median())

    K = df.strike.to_numpy(float)
    P = df.ltp.to_numpy(float)
    kind = df.kind.to_numpy()
    with np.errstate(all="ignore"):
        iv = implied_vol_b76(P, np.full(len(df), F), K, np.full(len(df), T), RISK_FREE, kind)
        g = greeks_b76(np.full(len(df), F), K, np.full(len(df), T), RISK_FREE, iv, kind)
    df["gex_cr"] = g["gamma"] * df.oi.to_numpy(float) * F * F * 0.01 / CR
    by_k = df.dropna(subset=["gex_cr"]).groupby("strike")["gex_cr"].sum()
    if by_k.empty:
        return None
    total = float(by_k.sum())
    kmax = float(by_k.idxmax())
    conc = float(by_k.max() / total) if total else None

    atm_k = float(piv.index[np.abs(piv.index - F).argmin()])
    atm_iv = float(np.nanmean(iv[np.isclose(K, atm_k)]))
    straddle = float(piv.loc[atm_k].sum()) if atm_k in piv.index else None

    # Spot vs derivatives divergence. The parity forward F is where the chain
    # is actually pricing the underlying; the index spot is the published
    # level. They should agree to within cost-of-carry (a few pts near expiry).
    # A larger gap is a real dislocation — the new-timings close print stood
    # ~150-200 pts above the late tape on both days it was first seen. Surface
    # it, never auto-discard: it may be a bad tick OR a genuine dislocation.
    spot = payload.get("spot")
    divergence = round(float(spot) - F, 1) if spot else None
    divergence_flag = divergence is not None and abs(divergence) > DIVERGENCE_FLAG_PTS

    regime = regime_from_concentration(conc)
    return {
        "expiry": near,
        "forward": round(F, 1),
        "spot": spot,
        "divergence": divergence,
        "divergence_flag": divergence_flag,
        "total_gex_cr": round(total, 0),
        "max_gamma_strike": kmax,
        "concentration": round(conc, 3) if conc else None,
        "atm_strike": atm_k,
        "atm_iv": round(atm_iv, 4) if np.isfinite(atm_iv) else None,
        "atm_straddle": round(straddle, 1) if straddle else None,
        "regime": regime,
        "top_strikes": {f"{k:.0f}": round(v, 0) for k, v in by_k.sort_values(ascending=False).head(5).items()},
    }


def store_daily(day: str, database_url: Optional[str] = None, times=("10:00", "13:00", "15:15")) -> int:
    from app.microstructure.materialize import _resolve_url

    engine = create_engine(_resolve_url(database_url))
    _metadata.create_all(engine, checkfirst=True)
    n = 0
    try:
        with engine.begin() as conn:
            for hm in times:
                h, m = map(int, hm.split(":"))
                tm = h * 60 + m - 330
                df = pd.read_sql(text("""
                    select g.strike, g.gamma, g.iv, g.underlying, g.expiry, b.oi_close
                    from option_greeks_minute g
                    join option_minute_bars b
                      on b.contract_id=g.contract_id and b.minute=g.minute
                    where date(g.minute)=:d and g.minute::time=:t and g.gamma is not null
                      and g.expiry=(select min(expiry) from option_greeks_minute where date(minute)=:d)
                """), conn, params={"d": day, "t": f"{tm // 60:02d}:{tm % 60:02d}:00"})
                if df.empty:
                    continue
                df["gex_cr"] = df.gamma * df.oi_close * df.underlying ** 2 * 0.01 / CR
                by_k = df.groupby("strike")["gex_cr"].sum()
                total = float(by_k.sum())
                F = float(df.underlying.iloc[0])
                atm = df.assign(dist=(df.strike - F).abs())
                conn.execute(text("""
                    delete from gamma_profile_daily where session_date=:d and snap_time=:t
                """), {"d": day, "t": hm})
                conn.execute(gamma_profile_daily.insert().values(
                    session_date=date.fromisoformat(day), snap_time=hm, expiry=pd.to_datetime(df.expiry.iloc[0]).date(),
                    forward=F, total_gex_cr=round(total, 0),
                    max_gamma_strike=float(by_k.idxmax()),
                    concentration=round(float(by_k.max() / total), 3) if total else None,
                    atm_iv=float(atm.loc[atm.dist == atm.dist.min(), "iv"].mean()),
                    computed_at=datetime.now(timezone.utc),
                ))
                n += 1
    finally:
        engine.dispose()
    return n
