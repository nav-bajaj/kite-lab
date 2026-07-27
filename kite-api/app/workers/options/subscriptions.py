"""Subscription management: the day's token set + widen-only adjustment.

Policy (PLAN.md, decided 2026-07-27): the window widens when spot's nearest
strike drifts >= N strikes from the last widen point, and never shrinks or
re-centers intraday — unsubscribing punches holes in a contract's bar
history. Morning selection re-centers the next day.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

from app.workers.options.instrument_loader import (
    Contract,
    Selection,
    atm_strike,
    strike_grid,
    strikes_to_add,
    _nifty_rows,
    _to_contract,
    normalize_rows,
)

log = logging.getLogger("options_worker.subscriptions")


class SubscriptionManager:
    def __init__(self, selection: Selection, nfo_rows: Sequence[dict], strike_window: int, drift_strikes: int):
        self.selection = selection
        self.strike_window = strike_window
        self.drift_strikes = drift_strikes
        self.rows = normalize_rows(nfo_rows)
        # full day grids per tracked expiry — the widen universe
        self.grids: Dict = {e: strike_grid(self.rows, e) for e in selection.option_expiries}
        self.subscribed_strikes: Dict = {
            e: sorted({c.strike for c in selection.contracts if c.kind in ("CE", "PE") and c.expiry == e})
            for e in selection.option_expiries
        }
        self.last_widen_atm: float = selection.atm_strike
        self.widen_events: int = 0

    def tokens(self) -> List[int]:
        return self.selection.tokens

    def on_spot(self, spot_price: float) -> List[Contract]:
        """Called per spot tick. Returns contracts to additionally subscribe
        (usually empty). Cheap: one nearest-strike lookup unless drifting."""
        near_grid = self.grids[self.selection.option_expiries[0]]
        nearest = atm_strike(near_grid, spot_price)
        step = self.selection.strike_step
        if abs(nearest - self.last_widen_atm) < self.drift_strikes * step:
            return []

        additions: List[Contract] = []
        for expiry in self.selection.option_expiries:
            grid = self.grids[expiry]
            new_atm = atm_strike(grid, spot_price)
            add_strikes = strikes_to_add(self.subscribed_strikes[expiry], grid, new_atm, self.strike_window)
            if not add_strikes:
                continue
            wanted = set(add_strikes)
            for r in _nifty_rows(self.rows, ("CE", "PE")):
                if r["expiry"] == expiry and r["strike"] in wanted:
                    additions.append(_to_contract(r, r["instrument_type"]))
            self.subscribed_strikes[expiry] = sorted(set(self.subscribed_strikes[expiry]) | wanted)

        self.last_widen_atm = nearest
        if additions:
            self.widen_events += 1
            self.selection.contracts.extend(additions)
            log.info(
                "widen #%d: spot=%.2f nearest=%g -> +%d contracts (%d strikes)",
                self.widen_events, spot_price, nearest, len(additions),
                len({c.strike for c in additions}),
            )
        return additions
