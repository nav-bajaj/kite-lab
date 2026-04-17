"""
FIFO trade matching service.

Walks trades in chronological order per symbol and produces `trade_matches`
rows that pair each SELL with the earliest still-open BUY lot(s). Realized
P&L is computed net of slippage using effective prices:

    effective_buy_price  = (notional + slippage) / shares
    effective_sell_price = (notional - slippage) / shares

Slippage is allocated pro-rata by matched-share fraction when a lot is only
partially consumed by a SELL (or consumed across multiple SELLs).

The service is idempotent: `rebuild_matches(universe)` wipes the universe's
existing matches and rebuilds from scratch, so it can be safely re-run as
part of the sync pipeline.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, List

from sqlalchemy.orm import Session

from app.models.database import get_session_local
from app.models.models import Trade, TradeMatch


ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")


@dataclass
class _OpenLot:
    """A still-open BUY lot in the FIFO queue."""

    buy_trade_id: int
    entry_date: object  # datetime.date
    remaining_shares: Decimal
    price: Decimal          # raw mid-price (buy.price)
    slippage_per_share: Decimal  # buy.slippage / buy.shares (pre-computed)


@dataclass
class RebuildResult:
    universe: str
    matches_created: int = 0
    unmatched_sell_shares: Decimal = field(default_factory=lambda: Decimal("0"))
    open_lots_remaining: int = 0
    open_shares_remaining: Decimal = field(default_factory=lambda: Decimal("0"))


def _dec(x) -> Decimal:
    """Coerce Numeric/float/int to Decimal safely."""
    if x is None:
        return ZERO
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _compute_matches(trades: Iterable[Trade]) -> tuple[List[dict], Decimal, dict]:
    """
    Pure FIFO matcher. Given trades ordered by (date, id) ascending, return:

        (match_rows, unmatched_sell_shares, open_lots_by_symbol)

    where `match_rows` is a list of dicts ready to insert into `trade_matches`.
    Doesn't touch the database.
    """
    open_lots: dict[str, deque[_OpenLot]] = defaultdict(deque)
    matches: list[dict] = []
    unmatched_sells = ZERO

    for t in trades:
        shares = _dec(t.shares)
        if shares <= 0:
            continue
        price = _dec(t.price)
        slip_total = _dec(t.slippage)
        # Slippage per share on this trade (pro-rata allocation basis).
        slip_per_share = (slip_total / shares) if shares else ZERO

        if t.side == "BUY":
            open_lots[t.symbol].append(
                _OpenLot(
                    buy_trade_id=t.id,
                    entry_date=t.trade_date,
                    remaining_shares=shares,
                    price=price,
                    slippage_per_share=slip_per_share,
                )
            )
            continue

        # SELL: consume FIFO lots
        remaining_to_match = shares
        queue = open_lots[t.symbol]
        while remaining_to_match > 0 and queue:
            lot = queue[0]
            matched = min(remaining_to_match, lot.remaining_shares)

            effective_buy = lot.price + lot.slippage_per_share
            effective_sell = price - slip_per_share
            pnl = (effective_sell - effective_buy) * matched
            if effective_buy > 0:
                pnl_pct = (effective_sell / effective_buy - Decimal("1")) * ONE_HUNDRED
            else:
                pnl_pct = ZERO
            holding_days = (t.trade_date - lot.entry_date).days

            matches.append(
                {
                    "universe": t.universe,
                    "buy_trade_id": lot.buy_trade_id,
                    "sell_trade_id": t.id,
                    "symbol": t.symbol,
                    "shares_matched": matched,
                    "entry_date": lot.entry_date,
                    "exit_date": t.trade_date,
                    "entry_price": effective_buy,
                    "exit_price": effective_sell,
                    "holding_days": holding_days,
                    "realized_pnl": pnl,
                    "realized_pnl_pct": pnl_pct,
                }
            )

            lot.remaining_shares -= matched
            remaining_to_match -= matched
            if lot.remaining_shares <= 0:
                queue.popleft()

        if remaining_to_match > 0:
            unmatched_sells += remaining_to_match

    return matches, unmatched_sells, open_lots


def rebuild_matches(universe: str, session: Session) -> RebuildResult:
    """
    Wipe and rebuild all `trade_matches` rows for one universe.

    Uses a single transaction. Caller owns session lifecycle.
    """
    trades = (
        session.query(Trade)
        .filter(Trade.universe == universe)
        .order_by(Trade.trade_date.asc(), Trade.id.asc())
        .all()
    )

    match_rows, unmatched, open_lots = _compute_matches(trades)

    session.query(TradeMatch).filter(TradeMatch.universe == universe).delete(
        synchronize_session=False
    )
    if match_rows:
        session.bulk_insert_mappings(TradeMatch, match_rows)
    session.commit()

    open_lot_count = sum(len(q) for q in open_lots.values())
    open_shares = sum(
        (lot.remaining_shares for q in open_lots.values() for lot in q),
        ZERO,
    )

    return RebuildResult(
        universe=universe,
        matches_created=len(match_rows),
        unmatched_sell_shares=unmatched,
        open_lots_remaining=open_lot_count,
        open_shares_remaining=open_shares,
    )


def rebuild_all_universes(
    universes: Iterable[str] = ("nse500", "nifty100", "nifty250"),
    session: Session | None = None,
) -> dict[str, RebuildResult]:
    """Convenience: rebuild matches for every universe in sequence."""
    owns_session = session is None
    if owns_session:
        SessionLocal = get_session_local()
        session = SessionLocal()
    try:
        return {u: rebuild_matches(u, session) for u in universes}
    finally:
        if owns_session:
            session.close()
