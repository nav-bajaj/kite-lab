"""Replay recorded raw ticks through the minute-bar aggregator.

Runs where the Parquet lives (the worker container, or locally against a
local capture):

    python -m app.workers.options.replay --date 2026-07-28            # build + report
    python -m app.workers.options.replay --date 2026-07-28 --validate # + compare vs Zerodha official bars
    python -m app.workers.options.replay --date 2026-07-28 --insert   # + write bars to option_minute_bars

Purposes: (1) prove the aggregator against the exchange's own minute
bars for the same session; (2) retroactively convert any recorded day's
ticks into DB bars (the raw Parquet is the authoritative archive, so
bars are always reconstructible).

Bars are bucketed on exchange timestamps — that is the clock Zerodha's
official candles use; recv_ts is only a fallback when exch_ts is absent.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from app.services.market_service import IST
from app.workers.options import instrument_loader as il
from app.workers.options.aggregator import MinuteBuilder
from app.workers.options.config import get_worker_settings


def load_ticks(day: str):
    import pandas as pd

    settings = get_worker_settings()
    day_dir = settings.ticks_dir / f"date={day}"
    files = sorted(day_dir.glob("*.parquet"))
    if not files:
        raise SystemExit(f"no tick files under {day_dir}")
    df = pd.concat(pd.read_parquet(f) for f in files)
    df = df.sort_values("recv_ts", kind="stable")
    return df, len(files)


def replay_day(day: str):
    """Feed the day's recorded ticks through MinuteBuilder; return rows."""
    settings = get_worker_settings()
    sel = il.load_selection(settings.tokens_dir / f"{day}.json")
    contracts = {c.instrument_token: c for c in sel.contracts}

    df, n_files = load_ticks(day)
    builder = MinuteBuilder()
    rows = []
    skipped = 0
    for t in df.itertuples(index=False):
        c = contracts.get(t.instrument_token)
        if c is None:
            skipped += 1
            continue
        ts = t.exch_ts if getattr(t, "exch_ts", None) is not None else t.recv_ts
        ts = ts.tz_localize(IST) if ts.tzinfo is None else ts.tz_convert(IST)
        tick = {
            "last_price": t.ltp,
            "volume_traded": t.volume,
            "oi": t.oi,
            "total_buy_quantity": t.total_buy_qty,
            "total_sell_quantity": t.total_sell_qty,
            "depth": {
                "buy": [{"price": t.bid1_price, "quantity": t.bid1_qty, "orders": 0}],
                "sell": [{"price": t.ask1_price, "quantity": t.ask1_qty, "orders": 0}],
            }
            if getattr(t, "bid1_price", 0)
            else None,
        }
        rows.extend(builder.add(tick, c, ts.to_pydatetime()))
    rows.extend(builder.close_all())
    print(f"replayed {len(df)} ticks from {n_files} files -> {len(rows)} bars "
          f"({len({r['contract_id'] for r in rows})} contracts, {skipped} skipped ticks)")
    return rows


def validate(rows, day: str, sample: int):
    """Compare replayed bars vs Zerodha's official minute candles."""
    from app.workers.options.worker import _kite_client

    by_contract = defaultdict(dict)
    for r in rows:
        by_contract[r["contract_id"]][r["minute"].replace(tzinfo=None)] = r

    sel = il.load_selection(get_worker_settings().tokens_dir / f"{day}.json")
    by_id = {c.contract_id: c for c in sel.contracts}
    targets = [cid for cid in (
        "NIFTY_SPOT",
        f"NIFTY_{day.replace('-', '')}_FUT",
    ) if cid in by_contract]
    # + the most-ticked options
    opt_ids = sorted(
        (cid for cid in by_contract if by_id.get(cid) and by_id[cid].kind in ("CE", "PE")),
        key=lambda cid: -len(by_contract[cid]),
    )
    targets += opt_ids[: max(sample - len(targets), 1)]

    kite = _kite_client()
    day_d = date.fromisoformat(day)
    frm = datetime(day_d.year, day_d.month, day_d.day, 9, 0)
    to = datetime(day_d.year, day_d.month, day_d.day, 16, 0)

    print(f"\nvalidating {len(targets)} contracts against official minute candles:")
    overall_close_err = []
    for cid in targets:
        c = by_id[cid]
        candles = kite.historical_data(c.instrument_token, frm, to, "minute", oi=(c.kind != "SPOT"))
        ours = by_contract[cid]
        matched = close_exact = vol_exact = 0
        close_errs = []
        vol_diffs = []
        for candle in candles:
            m = candle["date"].replace(tzinfo=None)
            r = ours.get(m)
            if r is None:
                continue
            matched += 1
            err = abs(r["close"] - candle["close"])
            close_errs.append(err)
            if err < 1e-9:
                close_exact += 1
            dv = abs(r["volume"] - candle["volume"])
            vol_diffs.append(dv)
            if dv == 0:
                vol_exact += 1
        overall_close_err.extend(close_errs)
        n = len(candles)
        print(
            f"  {cid}: official={n} ours={len(ours)} matched={matched} "
            f"close_exact={close_exact}/{matched} vol_exact={vol_exact}/{matched} "
            f"max_close_err={max(close_errs) if close_errs else 0:.2f} "
            f"max_vol_diff={max(vol_diffs) if vol_diffs else 0}"
        )
    if overall_close_err:
        import statistics

        print(f"\nclose-price agreement: mean_abs_err={statistics.mean(overall_close_err):.4f} "
              f"across {len(overall_close_err)} matched minutes")


def insert(rows):
    from app.workers.options.bar_store import BarStore

    store = BarStore()
    n = store.insert_bars(rows, source="replay")
    print(f"inserted {n} bars (idempotent on conflict)")
    store.dispose()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--sample", type=int, default=8, help="contracts to validate")
    ap.add_argument("--insert", action="store_true")
    args = ap.parse_args()

    rows = replay_day(args.date)
    if args.validate:
        validate(rows, args.date, args.sample)
    if args.insert:
        insert(rows)


if __name__ == "__main__":
    main()
