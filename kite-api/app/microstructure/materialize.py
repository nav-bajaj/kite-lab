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

from app.microstructure.greeks import ENGINE_VERSION, greeks, implied_vol, t_years

log = logging.getLogger(__name__)

RISK_FREE = 0.065

_metadata = MetaData()

option_greeks_minute = Table(
    "option_greeks_minute",
    _metadata,
    Column("contract_id", String(40), primary_key=True),
    Column("minute", DateTime(timezone=True), primary_key=True),
    Column("expiry", Date),
    Column("strike", Float),
    Column("kind", String(4)),
    Column("underlying", Float),
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
    S = df["underlying"].to_numpy(dtype=float)
    K = df["strike"].to_numpy(dtype=float)
    P = df["close"].to_numpy(dtype=float)
    kind = df["kind"].to_numpy()

    with np.errstate(all="ignore"):
        iv = implied_vol(P, S, K, T, RISK_FREE, kind)
        g = greeks(S, K, T, RISK_FREE, iv, kind)

    now = datetime.now(timezone.utc)
    records = []
    for i in range(len(df)):
        records.append({
            "contract_id": df["contract_id"].iloc[i],
            "minute": ts.iloc[i].to_pydatetime(),
            "expiry": df["expiry"].iloc[i],
            "strike": float(K[i]),
            "kind": df["kind"].iloc[i],
            "underlying": None if np.isnan(S[i]) else float(S[i]),
            "iv": None if np.isnan(iv[i]) else float(iv[i]),
            "delta": None if np.isnan(g["delta"][i]) else float(g["delta"][i]),
            "gamma": None if np.isnan(g["gamma"][i]) else float(g["gamma"][i]),
            "vega": None if np.isnan(g["vega"][i]) else float(g["vega"][i]),
            "theta_day": None if np.isnan(g["theta"][i]) else float(g["theta"][i] / 365.0),
            "r": RISK_FREE,
            "engine_version": ENGINE_VERSION,
            "computed_at": now,
        })
    conn.execute(
        text("delete from option_greeks_minute where date(minute) = :d and engine_version = :v"),
        {"d": day, "v": ENGINE_VERSION},
    )
    conn.execute(option_greeks_minute.insert(), records)
    return len(records)


def run(days=None, all_days=False, database_url: Optional[str] = None) -> int:
    engine = create_engine(_resolve_url(database_url))
    _metadata.create_all(engine, checkfirst=True)
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
