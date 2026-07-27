"""Raw-tick Parquet recorder.

Flattens every FULL-mode tick to one row and flushes buffered rows to
date-partitioned Parquet part-files. Raw ticks are the replayable archive
(PLAN.md); minute bars in Postgres are the primary dataset (Phase 3).
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.workers.options.instrument_loader import Contract

log = logging.getLogger("options_worker.recorder")

FLUSH_ROWS = 5000


def flatten_tick(tick: dict, contract: Contract, recv_ts: datetime) -> dict:
    row = {
        "recv_ts": recv_ts,
        "exch_ts": tick.get("exchange_timestamp"),
        "contract_id": contract.contract_id,
        "instrument_token": tick.get("instrument_token"),
        "kind": contract.kind,
        "expiry": contract.expiry.isoformat() if contract.expiry else None,
        "strike": contract.strike,
        "ltp": float(tick.get("last_price", 0) or 0),
        "last_qty": int(tick.get("last_traded_quantity", 0) or 0),
        "volume": int(tick.get("volume_traded", 0) or 0),
        "oi": int(tick.get("oi", 0) or 0),
        "oi_day_high": int(tick.get("oi_day_high", 0) or 0),
        "oi_day_low": int(tick.get("oi_day_low", 0) or 0),
        "total_buy_qty": int(tick.get("total_buy_quantity", 0) or 0),
        "total_sell_qty": int(tick.get("total_sell_quantity", 0) or 0),
    }
    depth = tick.get("depth") or {}
    for i in range(5):
        for side, key in (("bid", "buy"), ("ask", "sell")):
            level = (depth.get(key) or [])
            level = level[i] if i < len(level) else {}
            row[f"{side}{i+1}_price"] = float(level.get("price", 0) or 0)
            row[f"{side}{i+1}_qty"] = int(level.get("quantity", 0) or 0)
            row[f"{side}{i+1}_orders"] = int(level.get("orders", 0) or 0)
    return row


class TickRecorder:
    def __init__(self, base_dir: Path, flush_rows: int = FLUSH_ROWS):
        self.base_dir = base_dir
        self.flush_rows = flush_rows
        self._buffer: List[dict] = []
        self._lock = threading.Lock()
        self.rows_written = 0
        self.files_written = 0

    def add(self, tick: dict, contract: Contract, recv_ts: datetime) -> None:
        with self._lock:
            self._buffer.append(flatten_tick(tick, contract, recv_ts))
            should_flush = len(self._buffer) >= self.flush_rows
        if should_flush:
            self.flush()

    def flush(self) -> Optional[Path]:
        with self._lock:
            if not self._buffer:
                return None
            rows, self._buffer = self._buffer, []
        import pandas as pd

        df = pd.DataFrame(rows)
        first_ts: datetime = rows[0]["recv_ts"]
        out_dir = self.base_dir / f"date={first_ts.date().isoformat()}"
        out_dir.mkdir(parents=True, exist_ok=True)
        # seq suffix: replayed fixtures reuse recorded recv_ts, so a
        # timestamp-only name would overwrite earlier part-files
        path = out_dir / f"nifty_{first_ts.strftime('%H%M%S')}_{self.files_written:05d}.parquet"
        df.to_parquet(path, index=False)
        self.rows_written += len(rows)
        self.files_written += 1
        log.debug("flushed %d rows -> %s", len(rows), path.name)
        return path

    def counters(self) -> Dict[str, int]:
        with self._lock:
            buffered = len(self._buffer)
        return {"rows_written": self.rows_written, "files_written": self.files_written, "buffered": buffered}
