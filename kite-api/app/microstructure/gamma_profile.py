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


gamma_profile_minute = Table(
    "gamma_profile_minute",
    _metadata,
    Column("session_date", Date, primary_key=True),
    Column("minute", DateTime(timezone=True), primary_key=True),
    Column("expiry", Date),
    Column("forward", Float),
    Column("total_gex_cr", Float),
    Column("max_gamma_strike", Float),
    Column("concentration", Float),
    Column("atm_iv", Float),
    Column("computed_at", DateTime(timezone=True)),
)

PROFILE_COLS = ["minute", "forward", "total_gex_cr", "max_gamma_strike",
                "concentration", "atm_iv"]


def profile_series(df: pd.DataFrame) -> pd.DataFrame:
    """Per-minute gamma profile from greeks+OI rows — the shared core.

    `df` needs minute, strike, gamma, iv, oi_close, underlying, already
    restricted to one expiry. Returns one row per minute.

    Both writers below go through this, so a concentration read means the
    same thing in gamma_profile_daily, gamma_profile_minute, the daily
    report and the day-plan. Two implementations of "concentration" would
    be a silent divergence nobody notices until a threshold is calibrated
    on one and applied to the other.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=PROFILE_COLS)
    d = df.dropna(subset=["gamma"]).copy()
    if d.empty:
        return pd.DataFrame(columns=PROFILE_COLS)

    for c in ("strike", "gamma", "iv", "oi_close", "underlying"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["gex_cr"] = d.gamma * d.oi_close * d.underlying ** 2 * 0.01 / CR

    by_k = d.groupby(["minute", "strike"], as_index=False)["gex_cr"].sum()
    agg = by_k.groupby("minute")["gex_cr"].agg(total="sum", peak="max")
    kmax = by_k.loc[by_k.groupby("minute")["gex_cr"].idxmax()].set_index("minute")["strike"]

    # ATM = the strike nearest that minute's own forward; average the pair
    d["_dist"] = (d.strike - d.underlying).abs()
    d["_min"] = d.groupby("minute")["_dist"].transform("min")
    atm_iv = d[d._dist == d._min].groupby("minute")["iv"].mean()

    out = pd.DataFrame({
        "forward": d.groupby("minute")["underlying"].first(),
        "total_gex_cr": agg.total,
        "max_gamma_strike": kmax,
        "atm_iv": atm_iv,
    })
    out["concentration"] = np.where(agg.total > 0, agg.peak / agg.total, np.nan)
    return out.reset_index()[PROFILE_COLS]


def _ist_minute_of_day(s) -> pd.Series:
    """Minute-of-day in IST. utc=True handles both the tz-aware Postgres
    column and the UTC-naive values SQLite hands back."""
    ist = pd.to_datetime(s, utc=True).dt.tz_convert("Asia/Kolkata")
    return ist.dt.hour * 60 + ist.dt.minute


def _day_greeks(conn, day: str) -> pd.DataFrame:
    """Near-expiry greeks + the OI they must be weighted by, for one day."""
    return pd.read_sql(text("""
        select g.minute, g.strike, g.kind, g.gamma, g.iv, g.underlying,
               g.expiry, b.oi_close
        from option_greeks_minute g
        join option_minute_bars b
          on b.contract_id=g.contract_id and b.minute=g.minute
        where date(g.minute)=:d and g.gamma is not null
          and g.expiry=(select min(expiry) from option_greeks_minute
                        where date(minute)=:d)
    """), conn, params={"d": day})


def store_intraday(day: str, database_url: Optional[str] = None,
                   step_minutes: int = 1) -> int:
    """Persist the per-minute profile for `day` into gamma_profile_minute.

    Resolution exists for the concentration SLOPE: at 3 snapshots a day it
    was a two-point estimate across three hours, which is too coarse to
    calibrate the state-conditioned risk thresholds the founder framework
    calls for (research/RESULTS_2026-08-18_gamma_positioning.md).
    """
    from app.microstructure.materialize import _resolve_url

    engine = create_engine(_resolve_url(database_url))
    _metadata.create_all(engine, checkfirst=True)
    try:
        with engine.begin() as conn:
            df = _day_greeks(conn, day)
            if df.empty:
                return 0
            if step_minutes > 1:
                df = df[_ist_minute_of_day(df.minute) % step_minutes == 0]
                if df.empty:
                    return 0
            prof = profile_series(df)
            if prof.empty:
                return 0
            expiry = pd.to_datetime(df.expiry.iloc[0]).date()
            sd = date.fromisoformat(day)
            now = datetime.now(timezone.utc)
            conn.execute(text(
                "delete from gamma_profile_minute where session_date=:d"), {"d": day})
            conn.execute(gamma_profile_minute.insert(), [
                dict(session_date=sd, minute=pd.to_datetime(r.minute).to_pydatetime(),
                     expiry=expiry, forward=_f(r.forward),
                     total_gex_cr=_f(r.total_gex_cr, 0),
                     max_gamma_strike=_f(r.max_gamma_strike),
                     # 5dp, not the daily table's 3: a 0.001 quantum is coarse
                     # relative to the minute-to-minute change we want to slope
                     concentration=_f(r.concentration, 5),
                     atm_iv=_f(r.atm_iv, 4), computed_at=now)
                for r in prof.itertuples()])
            return len(prof)
    finally:
        engine.dispose()


def _f(v, nd: Optional[int] = 1):
    """Float or None — never NaN, which Postgres and SQLite disagree about."""
    if v is None or (isinstance(v, float) and not math.isfinite(v)) or pd.isna(v):
        return None
    return round(float(v), nd) if nd is not None else float(v)


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


def store_daily(day: str, database_url: Optional[str] = None,
                times=("10:00", "13:00", "15:15")) -> int:
    """Persist the 3-snapshot profile rows for the day-type library.

    Shares profile_series() with store_intraday() — these rows are the
    same computation sampled at three minutes, not a second one.
    """
    from app.microstructure.materialize import _resolve_url

    engine = create_engine(_resolve_url(database_url))
    _metadata.create_all(engine, checkfirst=True)
    n = 0
    try:
        with engine.begin() as conn:
            df = _day_greeks(conn, day)
            if df.empty:
                return 0
            prof = profile_series(df)
            if prof.empty:
                return 0
            prof["hm"] = _ist_minute_of_day(prof.minute).map(
                lambda v: f"{v // 60:02d}:{v % 60:02d}")
            expiry = pd.to_datetime(df.expiry.iloc[0]).date()
            sd = date.fromisoformat(day)
            for hm in times:
                row = prof[prof.hm == hm]
                if row.empty:
                    continue
                r = row.iloc[0]
                conn.execute(text("""
                    delete from gamma_profile_daily where session_date=:d and snap_time=:t
                """), {"d": day, "t": hm})
                conn.execute(gamma_profile_daily.insert().values(
                    session_date=sd, snap_time=hm, expiry=expiry,
                    forward=_f(r.forward), total_gex_cr=_f(r.total_gex_cr, 0),
                    max_gamma_strike=_f(r.max_gamma_strike),
                    concentration=_f(r.concentration, 3),
                    atm_iv=_f(r.atm_iv, 4),
                    computed_at=datetime.now(timezone.utc),
                ))
                n += 1
    finally:
        engine.dispose()
    return n
