"""Unit tests for the Stage-3 signed-GEX probe cores.

Run directly (not part of the production suite, per tasks/ conventions):
    pytest tasks/options_data/research/test_signed_gex_probe.py
"""
import numpy as np
import pandas as pd
import pytest

from signed_gex_probe import (BUY, SELL, UNCLASSIFIED, attribute_minute,
                              classify_trade, contract_flow, signed_profile)


class TestClassifyTrade:
    def test_lift_at_ask_is_buy(self):
        assert classify_trade(100.0, prev_bid=99.0, prev_ask=100.0, prev_ltp=99.5) == BUY

    def test_through_the_ask_is_buy(self):
        assert classify_trade(100.5, prev_bid=99.0, prev_ask=100.0, prev_ltp=99.5) == BUY

    def test_hit_at_bid_is_sell(self):
        assert classify_trade(99.0, prev_bid=99.0, prev_ask=100.0, prev_ltp=99.5) == SELL

    def test_inside_spread_above_mid_is_buy(self):
        assert classify_trade(99.8, prev_bid=99.0, prev_ask=100.0, prev_ltp=99.0) == BUY

    def test_inside_spread_below_mid_is_sell(self):
        assert classify_trade(99.2, prev_bid=99.0, prev_ask=100.0, prev_ltp=99.9) == SELL

    def test_at_mid_falls_back_to_tick_rule(self):
        assert classify_trade(99.5, prev_bid=99.0, prev_ask=100.0, prev_ltp=99.0) == BUY
        assert classify_trade(99.5, prev_bid=99.0, prev_ask=100.0, prev_ltp=99.9) == SELL

    def test_no_book_tick_rule(self):
        assert classify_trade(100.0, prev_bid=0.0, prev_ask=0.0, prev_ltp=99.0) == BUY
        assert classify_trade(98.0, prev_bid=0.0, prev_ask=0.0, prev_ltp=99.0) == SELL

    def test_no_information_unclassified(self):
        assert classify_trade(99.0, prev_bid=0.0, prev_ask=0.0, prev_ltp=99.0) == UNCLASSIFIED

    def test_crossed_book_ask_priority(self):
        # crossed/locked snapshots: at-or-above-ask wins before the mid test
        assert classify_trade(99.0, prev_bid=99.5, prev_ask=99.0, prev_ltp=98.0) == BUY


class TestAttributeMinute:
    def test_aggressive_buying_makes_writers_shorter(self):
        a = attribute_minute(buy_qty=500, sell_qty=100, d_oi=400)
        assert a.writer_delta == -400
        assert a.opened_closed == 400
        assert a.transferred == 200

    def test_aggressive_selling_makes_writers_longer(self):
        a = attribute_minute(buy_qty=100, sell_qty=600, d_oi=-500)
        assert a.writer_delta == +500
        assert a.opened_closed == 500

    def test_oi_flat_is_pure_transfer(self):
        a = attribute_minute(buy_qty=300, sell_qty=300, d_oi=0)
        assert a.writer_delta == 0
        assert a.opened_closed == 0
        assert a.transferred == 600

    def test_doi_cannot_exceed_classified_volume(self):
        a = attribute_minute(buy_qty=100, sell_qty=0, d_oi=100000)
        assert a.opened_closed == 100
        assert a.transferred == 0


def _tick(ts, ltp, volume, oi, bid, ask):
    return {"exch_ts": pd.Timestamp(ts), "recv_ts": pd.Timestamp(ts),
            "ltp": ltp, "volume": volume, "oi": oi,
            "bid1_price": bid, "ask1_price": ask}


class TestContractFlow:
    def test_buy_sequence_classified_from_prior_quote(self):
        df = pd.DataFrame([
            _tick("2026-08-07 09:20:01", 100.0, 1000, 5000, 99.5, 100.0),
            _tick("2026-08-07 09:20:02", 100.0, 1200, 5100, 99.5, 100.0),  # lift 200 @ prior ask
            _tick("2026-08-07 09:20:03", 99.5, 1500, 5100, 99.5, 100.0),   # hit 300 @ prior bid
        ])
        f = contract_flow(df)
        assert len(f) == 1
        assert f.buy_qty.iloc[0] == 200
        assert f.sell_qty.iloc[0] == 300
        assert f.d_oi.iloc[0] == 0  # first minute has no prior-minute OI

    def test_volume_reset_not_counted_as_trade(self):
        df = pd.DataFrame([
            _tick("2026-08-07 09:20:01", 100.0, 5000, 5000, 99.5, 100.0),
            _tick("2026-08-07 09:20:02", 100.0, 100, 5000, 99.5, 100.0),  # reconnect reset
        ])
        f = contract_flow(df)
        assert f.buy_qty.iloc[0] == 0 and f.sell_qty.iloc[0] == 0

    def test_d_oi_is_minute_over_minute(self):
        df = pd.DataFrame([
            _tick("2026-08-07 09:20:01", 100.0, 1000, 5000, 99.5, 100.0),
            _tick("2026-08-07 09:21:01", 100.0, 1000, 5600, 99.5, 100.0),
        ])
        f = contract_flow(df)
        assert list(f.d_oi) == [0, 600]


class TestSignedProfile:
    def test_net_aggressive_call_buying_reads_short_gamma_building(self):
        # writers passively sell calls all day -> their gamma flow is negative
        flow = pd.DataFrame([
            {"minute": pd.Timestamp("2026-08-07 09:20"), "contract_id": "C24600",
             "strike": 24600.0, "kind": "CE", "expiry": "2026-08-11",
             "buy_qty": 1000, "sell_qty": 200, "unclassified_qty": 0,
             "d_oi": 800, "writer_delta": -800, "opened_closed": 800,
             "transferred": 400, "oi_close": 5800},
        ])
        greeks = pd.DataFrame([
            {"strike": 24600.0, "kind": "CE", "gamma": 0.001, "underlying": 24600.0},
        ])
        profile, summary = signed_profile(flow, greeks)
        assert summary["sign"] == "SHORT-GAMMA-BUILDING"
        assert profile.writer_gamma_cr.iloc[0] == pytest.approx(
            -800 * 0.001 * 24600.0 ** 2 * 0.01 / 1e7, rel=1e-3)
        assert summary["estimated"] is True
        assert summary["classified_pct"] == 100.0

    def test_only_near_expiry_counted(self):
        rows = []
        for expiry, delta in (("2026-08-11", -500), ("2026-08-18", +9000)):
            rows.append({"minute": pd.Timestamp("2026-08-07 09:20"),
                         "contract_id": f"C{expiry}", "strike": 24600.0,
                         "kind": "CE", "expiry": expiry, "buy_qty": max(delta, 0) or 500,
                         "sell_qty": max(-delta, 0), "unclassified_qty": 0,
                         "d_oi": -delta if delta < 0 else delta,
                         "writer_delta": delta, "opened_closed": abs(delta),
                         "transferred": 0, "oi_close": 1000})
        flow = pd.DataFrame(rows)
        greeks = pd.DataFrame([
            {"strike": 24600.0, "kind": "CE", "gamma": 0.001, "underlying": 24600.0},
        ])
        _, summary = signed_profile(flow, greeks)
        assert summary["sign"] == "SHORT-GAMMA-BUILDING"
