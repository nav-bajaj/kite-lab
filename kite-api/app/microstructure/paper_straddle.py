"""Paper short-straddle: the standing MAE ledger (founder framework,
research/NOTE_risk_thresholds.md).

Every session gets one paper trade — sell ATM straddle at ENTRY_T (fills
at bid), exit EXIT_T (at ask) — evaluated from minute bars. The point is
NOT the P&L; it is the per-session MAE row (worst excursion, when, how
long underwater, regime state at the worst point) that accumulates into
the distribution the future risk-threshold table is calibrated from.

compute_day() is pure given a DB connection; the worker's EOD hook
stores the row; the live endpoint reuses live_state() intraday.
"""
from __future__ import annotations

import json
import logging
from datetime import date as date_type, datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import (
    Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text,
    create_engine, text,
)

log = logging.getLogger(__name__)

ENTRY_T, EXIT_T = "09:20", "15:15"
LOT = 75

_metadata = MetaData()

paper_straddle_ledger = Table(
    "paper_straddle_ledger",
    _metadata,
    Column("session_date", Date, primary_key=True),
    Column("strike", Float),
    Column("entry_credit", Float),
    Column("final_pnl", Float),
    Column("mae", Float),
    Column("mae_time", String(5)),
    Column("underwater_minutes", Integer),
    Column("last_underwater", String(5)),
    Column("detail", Text),  # JSON: entry spot, exit cost, notes
    Column("computed_at", DateTime(timezone=True)),
)


def _bars(conn, day):
    df = pd.read_sql(text("""
        select minute, kind, strike, close, bid_close, ask_close
        from option_minute_bars
        where date(minute)=:d and kind in ('CE','PE')
          and expiry=(select min(expiry) from option_minute_bars
                      where date(minute)=:d and kind in ('CE','PE'))
    """), conn, params={"d": day})
    spot = pd.read_sql(text("""
        select minute, close from option_minute_bars
        where contract_id='NIFTY_SPOT' and date(minute)=:d order by minute
    """), conn, params={"d": day})
    for x in (df, spot):
        x["hm"] = pd.to_datetime(x["minute"], utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")
    return df, spot


def compute_day(conn, day: str) -> Optional[dict]:
    df, spot = _bars(conn, day)
    if df.empty or spot.empty or ENTRY_T not in set(spot.hm):
        return None
    s0 = float(spot.loc[spot.hm == ENTRY_T, "close"].iloc[0])
    strikes = np.sort(df.strike.unique())
    k = float(strikes[np.abs(strikes - s0).argmin()])

    def leg(hm, kind, col):
        m = df[(df.hm == hm) & (df.strike == k) & (df.kind == kind)]
        return float(m[col].iloc[0]) if not m.empty and pd.notna(m[col].iloc[0]) else None

    entry = [leg(ENTRY_T, kd, "bid_close") for kd in ("CE", "PE")]
    if None in entry:
        return None
    credit = sum(entry)

    piv = df[df.strike == k].pivot_table(index="hm", columns="kind", values="close", aggfunc="first").dropna()
    piv = piv[(piv.index >= ENTRY_T) & (piv.index <= EXIT_T)]
    pnl = credit - (piv.CE + piv.PE)
    mae_hm, mae = (pnl.idxmin(), float(pnl.min())) if not pnl.empty else (None, 0.0)
    underwater = pnl[pnl < 0]

    exit_legs = [leg(EXIT_T, kd, "ask_close") for kd in ("CE", "PE")]
    final = credit - sum(exit_legs) if None not in exit_legs else float(pnl.iloc[-1])

    return {
        "session_date": date_type.fromisoformat(day),
        "strike": k,
        "entry_credit": round(credit, 2),
        "final_pnl": round(float(final), 2),
        "mae": round(min(mae, 0.0), 2),
        "mae_time": mae_hm,
        "underwater_minutes": int(len(underwater)),
        "last_underwater": underwater.index[-1] if len(underwater) else None,
        "detail": json.dumps({"entry_spot": s0, "entry_time": ENTRY_T, "exit_time": EXIT_T,
                              "pnl_at_exit_marks": round(float(pnl.iloc[-1]), 2) if len(pnl) else None}),
    }


def store_day(day: str, database_url: Optional[str] = None) -> Optional[dict]:
    from app.microstructure.materialize import _resolve_url

    engine = create_engine(_resolve_url(database_url))
    _metadata.create_all(engine, checkfirst=True)
    try:
        with engine.begin() as conn:
            row = compute_day(conn, day)
            if row is None:
                return None
            conn.execute(text("delete from paper_straddle_ledger where session_date=:d"), {"d": day})
            conn.execute(paper_straddle_ledger.insert().values(**row, computed_at=datetime.now(timezone.utc)))
        return row
    finally:
        engine.dispose()


def render_section(row: Optional[dict]) -> list:
    out = ["## Paper straddle (MAE ledger)"]
    if not row:
        out.append("- not computable for this session")
        return out
    out.append(f"- Sold {row['strike']:.0f} straddle {ENTRY_T} for {row['entry_credit']:.1f} pts; "
               f"exit {EXIT_T}: **{row['final_pnl']:+.1f} pts** (₹{row['final_pnl'] * LOT:+,.0f}/lot)")
    out.append(f"- MAE {row['mae']:+.1f} at {row['mae_time']} | underwater {row['underwater_minutes']} min"
               + (f" (last at {row['last_underwater']})" if row['last_underwater'] else ""))
    return out
