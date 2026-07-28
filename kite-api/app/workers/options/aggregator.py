"""Minute-bar aggregation — ticks in, permanent history out (handover §12).

Incremental: the worker feeds every tick to ``MinuteBuilder.add``; once a
tick arrives in a later minute (or ``close_all`` runs at EOD), the closed
minute's bars are emitted for bulk insert. Pure logic, no I/O — replayable
offline against recorded Parquet.

Field semantics worth stating:
- ``volume`` on a tick is the day-cumulative traded quantity, so a bar's
  traded volume is last-in-bar minus last-of-previous-bar (first bar of
  the day uses the first tick's cumulative volume as its base).
- OI gets its own o/h/l/c — intraday OI paths are a primary reason this
  engine exists.
- Spread and depth-imbalance are tick-weighted means over the bar (they
  are microstructure state, not trade flow); quantities/quotes at close
  capture the end-of-bar book.
- A minute with no ticks produces NO row — gaps are real information and
  carry-forward bars would fake liquidity. Downstream must tolerate gaps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.workers.options.instrument_loader import Contract


def minute_floor(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0)


@dataclass
class _WorkingBar:
    contract: Contract
    minute: datetime
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume_base: int = 0  # cumulative volume before this bar
    volume_last: int = 0
    oi_open: int = 0
    oi_high: int = 0
    oi_low: int = 0
    oi_close: int = 0
    bid_close: float = 0.0
    ask_close: float = 0.0
    bid_qty_close: int = 0
    ask_qty_close: int = 0
    spread_sum: float = 0.0
    spread_n: int = 0
    imbalance_sum: float = 0.0
    imbalance_n: int = 0
    tick_count: int = 0

    def to_row(self) -> dict:
        c = self.contract
        return {
            "contract_id": c.contract_id,
            "kind": c.kind,
            "expiry": c.expiry,  # date object — the store column is Date
            "strike": c.strike,
            "minute": self.minute,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": max(self.volume_last - self.volume_base, 0),
            "oi_open": self.oi_open,
            "oi_high": self.oi_high,
            "oi_low": self.oi_low,
            "oi_close": self.oi_close,
            "bid_close": self.bid_close,
            "ask_close": self.ask_close,
            "bid_qty_close": self.bid_qty_close,
            "ask_qty_close": self.ask_qty_close,
            "avg_spread": (self.spread_sum / self.spread_n) if self.spread_n else None,
            "avg_depth_imbalance": (self.imbalance_sum / self.imbalance_n) if self.imbalance_n else None,
            "tick_count": self.tick_count,
        }


class MinuteBuilder:
    def __init__(self) -> None:
        self._working: Dict[str, _WorkingBar] = {}
        self._last_cum_volume: Dict[str, int] = {}
        self.bars_emitted = 0

    def add(self, tick: dict, contract: Contract, ts: datetime) -> List[dict]:
        """Apply one tick; returns rows for any bars this tick closes."""
        minute = minute_floor(ts)
        cid = contract.contract_id
        wb = self._working.get(cid)
        closed: List[dict] = []

        if wb is not None and minute > wb.minute:
            closed.append(self._close(cid, wb))
            wb = None

        ltp = float(tick.get("last_price", 0) or 0)
        oi = int(tick.get("oi", 0) or 0)
        cum_vol = int(tick.get("volume_traded", 0) or 0)

        if wb is None:
            wb = _WorkingBar(
                contract=contract,
                minute=minute,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
                volume_base=self._last_cum_volume.get(cid, cum_vol),
                oi_open=oi,
                oi_high=oi,
                oi_low=oi,
                oi_close=oi,
            )
            self._working[cid] = wb

        wb.close = ltp
        wb.high = max(wb.high, ltp)
        wb.low = min(wb.low, ltp) if wb.low else ltp
        wb.volume_last = cum_vol
        if oi:
            if not wb.oi_open:
                wb.oi_open = wb.oi_high = wb.oi_low = oi
            wb.oi_close = oi
            wb.oi_high = max(wb.oi_high, oi)
            wb.oi_low = min(wb.oi_low or oi, oi)
        wb.tick_count += 1

        depth = tick.get("depth") or {}
        buy = depth.get("buy") or []
        sell = depth.get("sell") or []
        if buy and sell:
            bid = float(buy[0].get("price", 0) or 0)
            ask = float(sell[0].get("price", 0) or 0)
            if bid and ask:
                wb.bid_close = bid
                wb.ask_close = ask
                wb.spread_sum += ask - bid
                wb.spread_n += 1
        tbq = int(tick.get("total_buy_quantity", 0) or 0)
        tsq = int(tick.get("total_sell_quantity", 0) or 0)
        if tbq or tsq:
            wb.bid_qty_close = tbq
            wb.ask_qty_close = tsq
            wb.imbalance_sum += (tbq - tsq) / (tbq + tsq)
            wb.imbalance_n += 1

        return closed

    def _close(self, cid: str, wb: _WorkingBar) -> dict:
        self._last_cum_volume[cid] = wb.volume_last
        del self._working[cid]
        self.bars_emitted += 1
        return wb.to_row()

    def close_all(self) -> List[dict]:
        """EOD: flush every working bar."""
        return [self._close(cid, wb) for cid, wb in list(self._working.items())]

    def working_count(self) -> int:
        return len(self._working)
