"""Backfill minute+OI history for the day's selected contracts.

Research probe (tasks/, not scripts/): pulls Zerodha historical minute
candles for every contract in the day's saved selection and writes one
combined Parquet. No depth exists in this API — that is what the live
worker records. Run from kite-api/ with the repo venv.

Usage: python ../tasks/options_data/research/backfill_history.py [days]
"""
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, ".")

import pandas as pd

from app.workers.options.worker import _kite_client
from app.workers.options import instrument_loader as il
from app.workers.options.config import get_worker_settings

REQUEST_GAP_S = 0.4  # historical API allows ~3 req/s


def main(days: int = 7) -> Path:
    settings = get_worker_settings()
    sel = il.load_selection(settings.tokens_dir / f"{date.today().isoformat()}.json")
    kite = _kite_client()

    frm = datetime.now() - timedelta(days=days)
    to = datetime.now()

    frames = []
    failed = []
    for i, c in enumerate(sel.contracts):
        try:
            candles = kite.historical_data(
                c.instrument_token, frm, to, "minute", oi=(c.kind != "SPOT")
            )
        except Exception as exc:
            failed.append((c.contract_id, str(exc)))
            continue
        if not candles:
            failed.append((c.contract_id, "no candles"))
            continue
        df = pd.DataFrame(candles)
        df["contract_id"] = c.contract_id
        df["kind"] = c.kind
        df["strike"] = c.strike
        df["expiry"] = c.expiry.isoformat() if c.expiry else None
        frames.append(df)
        if i % 20 == 0:
            print(f"{i + 1}/{len(sel.contracts)} {c.contract_id}: {len(candles)} candles")
        time.sleep(REQUEST_GAP_S)

    out = pd.concat(frames, ignore_index=True)
    out_dir = settings.options_data_dir / "history"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"minute_{date.today().isoformat()}_{days}d.parquet"
    out.to_parquet(path, index=False)
    print(f"\nwrote {len(out)} rows x {len(frames)} contracts -> {path}")
    if failed:
        print("FAILED:", failed)
    return path


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
