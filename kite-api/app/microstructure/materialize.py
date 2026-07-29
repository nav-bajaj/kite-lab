"""Materialize per-minute IV + Greeks over option_minute_bars.

    python -m app.microstructure.materialize [--date YYYY-MM-DD] [--all]

Reads option bars (CE/PE) + the matching spot bar per minute, inverts IV
from bar close, computes delta/gamma/vega/theta, and bulk-writes
option_greeks_minute. Idempotent per (contract_id, minute): recompute
under the same engine_version replaces via delete+insert per day slice.
Rows that cannot be computed (no spot bar that minute, below intrinsic,
expired) are written with NULL iv/greeks — presence of the row records
that the input existed and the answer is "not computable", per the
never-fabricate principle.

theta is stored PER DAY (annual/365) — the practitioner convention.
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import (
    Column, Date, DateTime, Float, MetaData, String, Table, create_engine, text,
)

from app.microstructure.greeks import greeks_b76, implied_vol_b76, t_years

log = logging.getLogger(__name__)

RISK_FREE = 0.065
ENGINE_VERSION = "b76-parityfwd-v1"
MIN_PARITY_PAIRS = 3

_metadata = MetaData()

option_greeks_minute = Table(
    "option_greeks_minute",
    _metadata,
    Column("contract_id", String(40), primary_key=True),
    Column("minute", DateTime(timezone=True), primary_key=True),
    Column("expiry", Date),
    Column("strike", Float),
    Column("kind", String(4)),
    Column("underlying", Float),  # the forward actually used
    Column("underlying_src", String(12)),  # 'parity' | 'spot_carry'
    Column("iv", Float),
    Column("delta", Float),
    Column("gamma", Float),
    Column("vega", Float),
    Column("theta_day", Float),
    Column("r", Float),
    Column("engine_version", String(24)),
    Column("computed_at", DateTime(timezone=True)),
)


def _resolve_url(database_url: Optional[str]) -> str:
    if database_url:
        return database_url
    from app.config import get_settings

    return get_settings().database_url


def materialize_day(conn, day: str) -> int:
    bars = pd.read_sql(text("""
        select contract_id, minute, expiry, strike, kind, close
        from option_minute_bars
        where kind in ('CE','PE') and date(minute) = :d
    """), conn, params={"d": day})
    if bars.empty:
        return 0
    spot = pd.read_sql(text("""
        select minute, close as underlying from option_minute_bars
        where contract_id='NIFTY_SPOT' and date(minute) = :d
    """), conn, params={"d": day})
    df = bars.merge(spot, on="minute", how="left")
    # sqlite returns DATE columns as strings; Postgres as date objects
    df["expiry"] = pd.to_datetime(df["expiry"]).dt.date

    ts = pd.to_datetime(df["minute"], utc=True)
    T = np.array([
        t_years(t.to_pydatetime(), e) if pd.notna(e) else 0.0
        for t, e in zip(ts, df["expiry"])
    ])
    df["T"] = T

    # Forward per (expiry, minute): put-call parity across strike pairs —
    # F = K + (C - P) e^{rT}. Model-free; validated 2026-07-29 (13 strikes,
    # std 0.56 pts, same-strike CE/PE IV gap -> 0.00). Fallback when fewer
    # than MIN_PARITY_PAIRS pairs exist: spot-carry S e^{rT} (the old
    # Stage-1 assumption), labeled so consumers can filter.
    pair_rows = df.pivot_table(index=["expiry", "minute", "strike"], columns="kind",
                               values="close", aggfunc="first")
    pair_rows = pair_rows.dropna() if {"CE", "PE"} <= set(pair_rows.columns) else pair_rows.iloc[0:0]
    if not pair_rows.empty:
        pr = pair_rows.reset_index()
        tmap = df.drop_duplicates(["expiry", "minute"]).set_index(["expiry", "minute"])["T"]
        pr = pr.merge(tmap.rename("T"), on=["expiry", "minute"])
        pr["F"] = pr["strike"] + (pr["CE"] - pr["PE"]) * np.exp(RISK_FREE * pr["T"])
        fw = pr.groupby(["expiry", "minute"]).agg(F=("F", "median"), n=("F", "size")).reset_index()
        fw = fw[fw["n"] >= MIN_PARITY_PAIRS][["expiry", "minute", "F"]]
    else:
        fw = pd.DataFrame(columns=["expiry", "minute", "F"])
    df = df.merge(fw, on=["expiry", "minute"], how="left")
    df["F"] = pd.to_numeric(df["F"], errors="coerce")

    spot_carry = df["underlying"].to_numpy(dtype=float) * np.exp(RISK_FREE * df["T"].to_numpy())
    F_used = np.where(np.isfinite(df["F"].to_numpy(dtype=float)), df["F"].to_numpy(dtype=float), spot_carry)
    src = np.where(np.isfinite(df["F"].to_numpy(dtype=float)), "parity", "spot_carry")

    K = df["strike"].to_numpy(dtype=float)
    P = df["close"].to_numpy(dtype=float)
    kind = df["kind"].to_numpy()
    T = df["T"].to_numpy()

    with np.errstate(all="ignore"):
        iv = implied_vol_b76(P, F_used, K, T, RISK_FREE, kind)
        g = greeks_b76(F_used, K, T, RISK_FREE, iv, kind)

    now = datetime.now(timezone.utc)
    records = []
    for i in range(len(df)):
        records.append({
            "contract_id": df["contract_id"].iloc[i],
            "minute": ts.iloc[i].to_pydatetime(),
            "expiry": df["expiry"].iloc[i],
            "strike": float(K[i]),
            "kind": df["kind"].iloc[i],
            "underlying": None if np.isnan(F_used[i]) else float(F_used[i]),
            "underlying_src": str(src[i]),
            "iv": None if np.isnan(iv[i]) else float(iv[i]),
            "delta": None if np.isnan(g["delta"][i]) else float(g["delta"][i]),
            "gamma": None if np.isnan(g["gamma"][i]) else float(g["gamma"][i]),
            "vega": None if np.isnan(g["vega"][i]) else float(g["vega"][i]),
            "theta_day": None if np.isnan(g["theta"][i]) else float(g["theta"][i] / 365.0),
            "r": RISK_FREE,
            "engine_version": ENGINE_VERSION,
            "computed_at": now,
        })
    # Deliberate replace: exactly one materialized engine version at a time.
    # Reproducibility lives in engine_version + git history, not in keeping
    # parallel copies (see PLAN.md — versioning decision).
    conn.execute(text("delete from option_greeks_minute where date(minute) = :d"), {"d": day})
    conn.execute(option_greeks_minute.insert(), records)
    return len(records)


def _ensure_schema(engine) -> None:
    _metadata.create_all(engine, checkfirst=True)
    # underlying_src added after first ship; patch existing tables in place
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE option_greeks_minute ADD COLUMN IF NOT EXISTS underlying_src VARCHAR(12)"))
            else:
                conn.execute(text("ALTER TABLE option_greeks_minute ADD COLUMN underlying_src VARCHAR(12)"))
    except Exception:
        pass  # column already exists


def run(days=None, all_days=False, database_url: Optional[str] = None) -> int:
    engine = create_engine(_resolve_url(database_url))
    _ensure_schema(engine)
    total = 0
    with engine.begin() as conn:
        if all_days:
            days = [str(r[0]) for r in conn.execute(
                text("select distinct date(minute) from option_minute_bars order by 1")
            )]
        for d in days or []:
            n = materialize_day(conn, d)
            total += n
            print(f"{d}: {n} rows")
    engine.dispose()
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", action="append", help="repeatable")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    run(days=args.date, all_days=args.all)
