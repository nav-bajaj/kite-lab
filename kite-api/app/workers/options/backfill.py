"""Seed option_minute_bars from Zerodha's historical API (handover: the
analysis layer should not start with empty tables).

    python -m app.workers.options.backfill --days 30 [--date 2026-07-28]

Pulls minute candles (+OI for F&O) for every contract in the given day's
saved selection and bulk-inserts them as source='hist'. Depth-derived
columns (spread, imbalance, book quantities) are NULL by design — that
data only exists where the live worker recorded it. Idempotent: the
(contract_id, minute) PK skips anything the live/replay path already
wrote, so live bars always win over backfill.

Coverage is naturally uneven: weekly options only exist from listing
(~2-3 weeks), monthlies longer, index/futures the full window.
"""
from __future__ import annotations

import argparse
import time
from datetime import date, datetime, timedelta

from app.workers.options import instrument_loader as il
from app.workers.options.bar_store import BarStore
from app.workers.options.config import get_worker_settings
from app.workers.options.worker import _kite_client

REQUEST_GAP_S = 0.4  # historical API ~3 req/s


def candles_to_rows(candles, contract) -> list:
    rows = []
    for c in candles:
        oi = int(c.get("oi", 0) or 0)
        rows.append(
            {
                "contract_id": contract.contract_id,
                "kind": contract.kind,
                "expiry": contract.expiry,
                "strike": contract.strike,
                "minute": c["date"],
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": int(c.get("volume", 0) or 0),
                "oi_open": oi, "oi_high": oi, "oi_low": oi, "oi_close": oi,
                "bid_close": None, "ask_close": None,
                "bid_qty_close": None, "ask_qty_close": None,
                "avg_spread": None, "avg_depth_imbalance": None,
                "tick_count": None,
            }
        )
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--date", default=date.today().isoformat(), help="selection date to backfill contracts for")
    args = ap.parse_args()

    settings = get_worker_settings()
    sel = il.load_selection(settings.tokens_dir / f"{args.date}.json")
    kite = _kite_client()
    store = BarStore()

    frm = datetime.now() - timedelta(days=args.days)
    to = datetime.now()
    total = 0
    failed = []
    for i, c in enumerate(sel.contracts):
        try:
            candles = kite.historical_data(c.instrument_token, frm, to, "minute", oi=(c.kind != "SPOT"))
            total += store.insert_bars(candles_to_rows(candles, c), source="hist")
        except Exception as exc:
            failed.append((c.contract_id, str(exc)))
        if i % 20 == 0:
            print(f"{i + 1}/{len(sel.contracts)} {c.contract_id}: cumulative rows {total}")
        time.sleep(REQUEST_GAP_S)

    print(f"backfilled {total} bar rows for {len(sel.contracts) - len(failed)} contracts")
    if failed:
        print("failed:", failed[:5], f"(+{len(failed) - 5} more)" if len(failed) > 5 else "")
    store.dispose()


if __name__ == "__main__":
    main()
