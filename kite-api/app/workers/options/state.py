"""In-memory market state — "the current market" (handover doc section 10).

Every incoming tick updates this object; nothing here writes to the
database. The aggregator (Phase 3) and the snapshot writer read from it.

Thread model: KiteTicker delivers ticks on its own thread while the worker
loop and health endpoint read from theirs, so mutations and multi-field
reads go through a lock.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from app.workers.options.instrument_loader import Contract


@dataclass
class DepthLevel:
    price: float = 0.0
    quantity: int = 0
    orders: int = 0


@dataclass
class ContractState:
    contract: Contract
    ltp: float = 0.0
    last_qty: int = 0
    volume: int = 0
    oi: int = 0
    oi_day_high: int = 0
    oi_day_low: int = 0
    total_buy_qty: int = 0
    total_sell_qty: int = 0
    bids: List[DepthLevel] = field(default_factory=list)
    asks: List[DepthLevel] = field(default_factory=list)
    exch_ts: Optional[datetime] = None
    recv_ts: Optional[datetime] = None
    tick_count: int = 0

    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0

    @property
    def spread(self) -> float:
        if self.bids and self.asks:
            return self.asks[0].price - self.bids[0].price
        return 0.0


def _parse_depth(side: List[dict]) -> List[DepthLevel]:
    return [
        DepthLevel(price=float(l.get("price", 0)), quantity=int(l.get("quantity", 0)), orders=int(l.get("orders", 0)))
        for l in side
    ]


class ChainState:
    def __init__(self, contracts: List[Contract]):
        self._lock = threading.Lock()
        self.by_token: Dict[int, ContractState] = {}
        self.by_id: Dict[str, ContractState] = {}
        self.spot_price: float = 0.0
        self.register(contracts)

    def register(self, contracts: List[Contract]) -> None:
        """Add contracts (initial set, or intraday widen additions)."""
        with self._lock:
            for c in contracts:
                if c.instrument_token in self.by_token:
                    continue
                cs = ContractState(contract=c)
                self.by_token[c.instrument_token] = cs
                self.by_id[c.contract_id] = cs

    def apply_tick(self, tick: dict, recv_ts: datetime) -> Optional[ContractState]:
        """Apply one KiteTicker tick dict. Index ticks (the spot) carry no
        depth/oi/volume — every field is optional except last_price."""
        cs = self.by_token.get(tick.get("instrument_token"))
        if cs is None:
            return None
        with self._lock:
            cs.ltp = float(tick.get("last_price", cs.ltp) or cs.ltp)
            cs.last_qty = int(tick.get("last_traded_quantity", cs.last_qty) or 0)
            cs.volume = int(tick.get("volume_traded", cs.volume) or 0)
            cs.oi = int(tick.get("oi", cs.oi) or 0)
            cs.oi_day_high = int(tick.get("oi_day_high", cs.oi_day_high) or 0)
            cs.oi_day_low = int(tick.get("oi_day_low", cs.oi_day_low) or 0)
            cs.total_buy_qty = int(tick.get("total_buy_quantity", cs.total_buy_qty) or 0)
            cs.total_sell_qty = int(tick.get("total_sell_quantity", cs.total_sell_qty) or 0)
            depth = tick.get("depth") or {}
            if depth.get("buy"):
                cs.bids = _parse_depth(depth["buy"])
            if depth.get("sell"):
                cs.asks = _parse_depth(depth["sell"])
            cs.exch_ts = tick.get("exchange_timestamp") or cs.exch_ts
            cs.recv_ts = recv_ts
            cs.tick_count += 1
            if cs.contract.kind == "SPOT":
                self.spot_price = cs.ltp
        return cs

    # -- read views --------------------------------------------------------

    def chain_view(self) -> dict:
        """{expiry: {strike: {"CE": ContractState, "PE": ContractState}}}"""
        with self._lock:
            view: dict = {}
            for cs in self.by_id.values():
                c = cs.contract
                if c.kind not in ("CE", "PE"):
                    continue
                view.setdefault(c.expiry, {}).setdefault(c.strike, {})[c.kind] = cs
            return view

    def staleness_seconds(self, now: datetime) -> Optional[float]:
        """Age of the freshest tick — the 'is the feed alive' number.
        (Per-contract ages vary hugely: far strikes legitimately tick rarely.)"""
        with self._lock:
            latest = [cs.recv_ts for cs in self.by_id.values() if cs.recv_ts]
        if not latest:
            return None
        return (now - max(latest)).total_seconds()

    def counters(self) -> dict:
        with self._lock:
            ticked = sum(1 for cs in self.by_id.values() if cs.tick_count)
            total_ticks = sum(cs.tick_count for cs in self.by_id.values())
            return {
                "contracts": len(self.by_id),
                "contracts_ticked": ticked,
                "total_ticks": total_ticks,
                "spot_price": self.spot_price,
            }
