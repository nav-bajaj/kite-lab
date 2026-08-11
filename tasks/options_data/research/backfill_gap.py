"""Fill an intraday capture gap from Zerodha minute candles (source='hist').

Built for the 2026-08-11 outage (ticker dead 09:15-11:33 IST). Zerodha has
no historical tick API, so the gap heals at minute-candle resolution:
OHLC/volume/OI real, depth columns NULL by design (that data only exists
where the live worker recorded it). Idempotent — the (contract_id, minute)
PK means live bars always win.

Contract universe comes from the day's live bars in the DB (the widened
set is a superset of the morning selection), tokens resolved against the
current NFO instruments dump — run the SAME day as the gap: expired
weeklies drop out of the dump after expiry day.

Run (laptop, credentials via the DB kite_session row):
  railway run --service Postgres -- python backfill_gap.py \
      --date 2026-08-11 --start 09:15 --end 11:35 [--validate-only]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import namedtuple
from datetime import datetime

# Must precede app imports: under `railway run` DATABASE_URL is the
# internal hostname, unreachable from the laptop.
if os.environ.get("DATABASE_PUBLIC_URL"):
    os.environ["DATABASE_URL"] = os.environ["DATABASE_PUBLIC_URL"]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../kite-api"))

import pandas as pd
from sqlalchemy import create_engine, text

NIFTY_SPOT_TOKEN = 256265
Contract = namedtuple("Contract", "contract_id kind expiry strike instrument_token")


def day_contracts(conn, day: str) -> list:
    df = pd.read_sql(text("""
        select distinct contract_id, kind, expiry, strike
        from option_minute_bars where date(minute)=:d and source='live'
    """), conn, params={"d": day})
    return df.to_dict(orient="records")


def resolve_tokens(kite, rows: list) -> tuple:
    nfo = pd.DataFrame(kite.instruments("NFO"))
    nfo = nfo[nfo.name == "NIFTY"]
    nfo["expiry"] = pd.to_datetime(nfo.expiry).dt.date
    by_key = {(r.expiry.isoformat(), float(r.strike), r.instrument_type): int(r.instrument_token)
              for r in nfo.itertuples()}
    fut_by_expiry = {r.expiry.isoformat(): int(r.instrument_token)
                     for r in nfo.itertuples() if r.instrument_type == "FUT"}
    contracts, missing = [], []
    for r in rows:
        expiry = r["expiry"].isoformat() if r["expiry"] else None
        if r["kind"] == "SPOT":
            token = NIFTY_SPOT_TOKEN
        elif r["kind"] == "FUT":
            token = fut_by_expiry.get(expiry)
        else:
            token = by_key.get((expiry, float(r["strike"]), r["kind"]))
        if token is None:
            missing.append(r["contract_id"])
            continue
        contracts.append(Contract(r["contract_id"], r["kind"], r["expiry"], r["strike"], token))
    return contracts, missing


def gap_minutes(conn, day: str, start: str, end: str) -> pd.DataFrame:
    return pd.read_sql(text("""
        select to_char(minute at time zone 'Asia/Kolkata', 'HH24:MI') hm, count(*) n
        from option_minute_bars where date(minute)=:d
          and to_char(minute at time zone 'Asia/Kolkata', 'HH24:MI') between :s and :e
        group by 1 order by 1
    """), conn, params={"d": day, "s": start, "e": end})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--start", default="09:15")
    ap.add_argument("--end", default="11:35")
    ap.add_argument("--validate-only", action="store_true",
                    help="compare hist candles vs live bars on an overlap window; write nothing")
    args = ap.parse_args()

    from app.workers.options.backfill import candles_to_rows
    from app.workers.options.bar_store import BarStore
    from app.workers.options.worker import _kite_client

    engine = create_engine(os.environ["DATABASE_URL"])
    kite = _kite_client()
    day = args.date

    with engine.connect() as conn:
        rows = day_contracts(conn, day)
        before = gap_minutes(conn, day, args.start, args.end)
    contracts, missing = resolve_tokens(kite, rows)
    print(f"{len(contracts)} contracts resolved, {len(missing)} unresolved: {missing[:5]}")
    print(f"window {args.start}-{args.end}: {len(before)} minutes present before fill "
          f"(mean contracts/minute {before.n.mean():.0f})" if not before.empty
          else f"window {args.start}-{args.end}: EMPTY before fill")

    frm = datetime.fromisoformat(f"{day} {args.start}")
    to = datetime.fromisoformat(f"{day} {args.end}")

    if args.validate_only:
        # Overlap check on a live-covered window: hist candle close must
        # match the live bar close (same construction, tick-derived).
        sample = [c for c in contracts if c.kind in ("CE", "PE")][:3]
        with engine.connect() as conn:
            for c in sample:
                candles = kite.historical_data(c.instrument_token, frm, to, "minute",
                                               oi=True)
                hist = pd.DataFrame(candles)
                live = pd.read_sql(text("""
                    select minute, close from option_minute_bars
                    where contract_id=:cid and date(minute)=:d and source='live'
                """), conn, params={"cid": c.contract_id, "d": day})
                if hist.empty or live.empty:
                    print(f"  {c.contract_id}: no overlap to validate")
                    continue
                hist["minute"] = pd.to_datetime(hist.date, utc=True)
                m = live.merge(hist[["minute", "close"]], on="minute",
                               suffixes=("_live", "_hist"))
                if m.empty:
                    print(f"  {c.contract_id}: no overlapping minutes")
                    continue
                err = (m.close_live - m.close_hist).abs()
                print(f"  {c.contract_id}: {len(m)} overlap minutes, "
                      f"mean |close err| {err.mean():.4f}, max {err.max():.4f}")
        return

    store = BarStore()
    total, failed = 0, []
    for i, c in enumerate(contracts):
        try:
            candles = kite.historical_data(c.instrument_token, frm, to, "minute",
                                           oi=(c.kind != "SPOT"))
            total += store.insert_bars(candles_to_rows(candles, c), source="hist")
        except Exception as exc:
            failed.append((c.contract_id, str(exc)))
        if i % 20 == 0:
            print(f"{i + 1}/{len(contracts)} {c.contract_id}: cumulative inserted {total}")
        time.sleep(0.4)
    store.dispose()

    with engine.connect() as conn:
        after = gap_minutes(conn, day, args.start, args.end)
    print(f"inserted {total} hist rows; window now {len(after)} minutes "
          f"(mean contracts/minute {after.n.mean():.0f})")
    if failed:
        print("failed:", failed[:5], f"(+{len(failed) - 5} more)" if len(failed) > 5 else "")


if __name__ == "__main__":
    main()
