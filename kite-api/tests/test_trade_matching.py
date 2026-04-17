"""Unit tests for the FIFO trade matching service."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from app.services.trade_matching_service import _compute_matches


@dataclass
class _FakeTrade:
    """Duck-type Trade rows for pure-function tests (no DB required)."""

    id: int
    universe: str
    trade_date: date
    symbol: str
    side: str
    shares: Decimal
    price: Decimal
    slippage: Decimal


def _t(id, d, symbol, side, shares, price, slip_rate=Decimal("0.002"), universe="nse500"):
    notional = Decimal(shares) * Decimal(price)
    slippage = notional * slip_rate
    return _FakeTrade(
        id=id,
        universe=universe,
        trade_date=d,
        symbol=symbol,
        side=side,
        shares=Decimal(shares),
        price=Decimal(price),
        slippage=slippage,
    )


def test_single_buy_single_sell_one_to_one():
    """Basic 1 BUY -> 1 SELL: one match, correct effective-price P&L."""
    trades = [
        _t(1, date(2026, 1, 1), "INFY", "BUY", 10, 1000),
        _t(2, date(2026, 1, 31), "INFY", "SELL", 10, 1100),
    ]
    matches, unmatched, open_lots = _compute_matches(trades)

    assert len(matches) == 1
    assert unmatched == 0
    assert sum(len(q) for q in open_lots.values()) == 0

    m = matches[0]
    assert m["buy_trade_id"] == 1
    assert m["sell_trade_id"] == 2
    assert m["shares_matched"] == Decimal(10)
    assert m["holding_days"] == 30
    # effective_buy  = 1000 + 2  = 1002
    # effective_sell = 1100 - 2.2 = 1097.8
    # pnl = (1097.8 - 1002) * 10 = 958.0
    assert m["entry_price"] == Decimal("1002")
    assert m["exit_price"] == Decimal("1097.8")
    assert m["realized_pnl"] == Decimal("958.0")
    # pnl_pct = (1097.8/1002 - 1) * 100 ≈ 9.5609%
    assert abs(m["realized_pnl_pct"] - Decimal("9.560878243512974")) < Decimal("0.0001")


def test_one_buy_two_partial_sells():
    """BUY 10 -> SELL 6, SELL 4 -> two matches summing to full position."""
    trades = [
        _t(1, date(2026, 1, 1), "X", "BUY", 10, 100),
        _t(2, date(2026, 1, 10), "X", "SELL", 6, 110),
        _t(3, date(2026, 1, 20), "X", "SELL", 4, 120),
    ]
    matches, unmatched, open_lots = _compute_matches(trades)

    assert len(matches) == 2
    assert unmatched == 0
    assert sum(len(q) for q in open_lots.values()) == 0

    assert matches[0]["buy_trade_id"] == 1
    assert matches[0]["sell_trade_id"] == 2
    assert matches[0]["shares_matched"] == Decimal(6)

    assert matches[1]["buy_trade_id"] == 1  # same buy, second slice
    assert matches[1]["sell_trade_id"] == 3
    assert matches[1]["shares_matched"] == Decimal(4)

    # Total matched shares = original buy size
    total = sum(m["shares_matched"] for m in matches)
    assert total == Decimal(10)


def test_two_buys_one_covering_sell_fifo_order():
    """BUY 5 @100 (day 1), BUY 5 @110 (day 2), SELL 8 (day 3) -> FIFO: 5 + 3."""
    trades = [
        _t(1, date(2026, 1, 1), "Y", "BUY", 5, 100),
        _t(2, date(2026, 1, 2), "Y", "BUY", 5, 110),
        _t(3, date(2026, 1, 5), "Y", "SELL", 8, 120),
    ]
    matches, unmatched, open_lots = _compute_matches(trades)

    assert len(matches) == 2
    assert unmatched == 0

    # First match: earliest lot (BUY #1), 5 shares
    assert matches[0]["buy_trade_id"] == 1
    assert matches[0]["shares_matched"] == Decimal(5)

    # Second match: BUY #2, 3 shares
    assert matches[1]["buy_trade_id"] == 2
    assert matches[1]["shares_matched"] == Decimal(3)

    # BUY #2 should have 2 shares remaining open
    remaining = sum(lot.remaining_shares for q in open_lots.values() for lot in q)
    assert remaining == Decimal(2)


def test_re_entry_pattern_makes_disjoint_pairs():
    """BUY -> SELL -> BUY -> SELL same symbol: two independent matches."""
    trades = [
        _t(1, date(2026, 1, 1), "Z", "BUY", 10, 100),
        _t(2, date(2026, 1, 10), "Z", "SELL", 10, 105),
        _t(3, date(2026, 2, 1), "Z", "BUY", 10, 95),
        _t(4, date(2026, 2, 20), "Z", "SELL", 10, 115),
    ]
    matches, unmatched, open_lots = _compute_matches(trades)

    assert len(matches) == 2
    assert unmatched == 0
    assert sum(len(q) for q in open_lots.values()) == 0

    assert matches[0]["buy_trade_id"] == 1
    assert matches[0]["sell_trade_id"] == 2
    assert matches[1]["buy_trade_id"] == 3
    assert matches[1]["sell_trade_id"] == 4


def test_unmatched_sell_warns_but_doesnt_crash():
    """SELL with no prior BUY: unmatched shares tracked, no match emitted."""
    trades = [
        _t(1, date(2026, 1, 1), "BAD", "SELL", 5, 100),
    ]
    matches, unmatched, _ = _compute_matches(trades)

    assert matches == []
    assert unmatched == Decimal(5)


def test_open_buy_at_end_of_history_produces_no_match():
    """BUY with no subsequent SELL is an open position."""
    trades = [
        _t(1, date(2026, 1, 1), "OPEN", "BUY", 10, 100),
    ]
    matches, unmatched, open_lots = _compute_matches(trades)

    assert matches == []
    assert unmatched == 0
    lots = list(open_lots["OPEN"])
    assert len(lots) == 1
    assert lots[0].remaining_shares == Decimal(10)


def test_pnl_reconciles_with_cash_flow():
    """
    Realized P&L summed across matches equals actual cash flow:
        sell_proceeds_net - buy_cost_net
    """
    trades = [
        _t(1, date(2026, 1, 1), "A", "BUY", 100, 50),
        _t(2, date(2026, 2, 1), "A", "SELL", 100, 55),
    ]
    matches, _, _ = _compute_matches(trades)

    # Cash flow reconstruction:
    buy_notional = Decimal(100) * Decimal(50)   # 5000
    buy_slip = buy_notional * Decimal("0.002")  # 10
    buy_cost_net = buy_notional + buy_slip       # 5010

    sell_notional = Decimal(100) * Decimal(55)  # 5500
    sell_slip = sell_notional * Decimal("0.002")  # 11
    sell_proceeds_net = sell_notional - sell_slip  # 5489

    expected_pnl = sell_proceeds_net - buy_cost_net  # 479

    assert matches[0]["realized_pnl"] == expected_pnl
