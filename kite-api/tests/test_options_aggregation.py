"""Phase 3: minute-bar aggregation + Postgres bar store.

Tick dicts are SYNTHETIC (kiteticker FULL shape, invented values). The
full-day replay against real recorded ticks + Zerodha's official bars
runs in tasks/options_data/research/replay_validate.py — this file covers
the pure math and the store contract.
"""
import gzip
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from app.services.market_service import IST
from app.workers.options import instrument_loader as il
from app.workers.options.aggregator import MinuteBuilder, minute_floor
from app.workers.options.bar_store import BarStore

FIXTURE = Path(__file__).parent / "fixtures" / "nfo_nifty_2026-07-27.json.gz"


@pytest.fixture(scope="module")
def contracts():
    with gzip.open(FIXTURE, "rb") as f:
        rows = il.normalize_rows(json.loads(f.read()))
    sel = il.select_contracts(rows, spot_price=23995.95, today=date(2026, 7, 27))
    return {c.contract_id: c for c in sel.contracts}


def tick(ltp, vol=0, oi=0, bid=None, ask=None, tbq=0, tsq=0):
    t = {"last_price": ltp, "volume_traded": vol, "oi": oi,
         "total_buy_quantity": tbq, "total_sell_quantity": tsq}
    if bid is not None:
        t["depth"] = {
            "buy": [{"price": bid, "quantity": 10, "orders": 1}],
            "sell": [{"price": ask, "quantity": 10, "orders": 1}],
        }
    return t


def ts(h, m, s):
    return IST.localize(datetime(2026, 7, 28, h, m, s))


class TestMinuteBuilder:
    def test_ohlc_and_close_on_minute_roll(self, contracts):
        c = contracts["NIFTY_20260728_24000_CE"]
        b = MinuteBuilder()
        assert b.add(tick(100, vol=1000, oi=500), c, ts(9, 15, 1)) == []
        assert b.add(tick(105, vol=1500, oi=600), c, ts(9, 15, 20)) == []
        assert b.add(tick(95, vol=2000, oi=550), c, ts(9, 15, 59)) == []
        closed = b.add(tick(98, vol=2100, oi=560), c, ts(9, 16, 0))
        assert len(closed) == 1
        bar = closed[0]
        assert (bar["open"], bar["high"], bar["low"], bar["close"]) == (100, 105, 95, 95)
        assert bar["minute"] == ts(9, 15, 0)
        assert (bar["oi_open"], bar["oi_high"], bar["oi_low"], bar["oi_close"]) == (500, 600, 500, 550)
        assert bar["tick_count"] == 3

    def test_volume_is_delta_of_cumulative(self, contracts):
        c = contracts["NIFTY_20260728_24000_CE"]
        b = MinuteBuilder()
        b.add(tick(100, vol=1000), c, ts(9, 15, 5))
        b.add(tick(101, vol=1800), c, ts(9, 15, 40))
        bar1 = b.add(tick(102, vol=2000), c, ts(9, 16, 3))[0]
        # first bar of the day: base = first tick's cumulative
        assert bar1["volume"] == 800
        bar2 = b.add(tick(103, vol=2600), c, ts(9, 17, 0))[0]
        # second bar: 2000 (its only tick) - 1800 (last of bar1)
        assert bar2["volume"] == 200

    def test_gap_minutes_produce_no_rows(self, contracts):
        c = contracts["NIFTY_20260728_24000_CE"]
        b = MinuteBuilder()
        b.add(tick(100, vol=100), c, ts(9, 15, 5))
        closed = b.add(tick(110, vol=300), c, ts(9, 19, 30))  # 3 silent minutes
        assert len(closed) == 1  # only 09:15 closes; nothing invented for 16-18
        bar = b.add(tick(111, vol=350), c, ts(9, 20, 0))[0]
        assert bar["minute"] == ts(9, 19, 0)
        assert bar["volume"] == 200  # 300 - 100, delta bridges the gap

    def test_spread_and_imbalance_tick_weighted(self, contracts):
        c = contracts["NIFTY_20260728_24000_CE"]
        b = MinuteBuilder()
        b.add(tick(100, bid=99.0, ask=100.0, tbq=600, tsq=400), c, ts(9, 15, 1))
        b.add(tick(100, bid=99.5, ask=100.0, tbq=300, tsq=700), c, ts(9, 15, 2))
        bar = b.add(tick(100), c, ts(9, 16, 0))[0]
        assert bar["avg_spread"] == pytest.approx(0.75)  # (1.0 + 0.5) / 2
        assert bar["avg_depth_imbalance"] == pytest.approx((0.2 - 0.4) / 2)
        assert bar["bid_close"] == 99.5 and bar["ask_close"] == 100.0
        assert bar["bid_qty_close"] == 300 and bar["ask_qty_close"] == 700

    def test_index_ticks_without_depth_or_oi(self, contracts):
        c = contracts["NIFTY_SPOT"]
        b = MinuteBuilder()
        b.add(tick(24000.0), c, ts(9, 15, 1))
        bar = b.add(tick(24010.0), c, ts(9, 16, 0))[0]
        assert bar["close"] == 24000.0
        assert bar["avg_spread"] is None
        assert bar["avg_depth_imbalance"] is None
        assert bar["volume"] == 0

    def test_close_all_flushes_working_bars(self, contracts):
        ce = contracts["NIFTY_20260728_24000_CE"]
        pe = contracts["NIFTY_20260728_24000_PE"]
        b = MinuteBuilder()
        b.add(tick(100, vol=10), ce, ts(15, 29, 30))
        b.add(tick(50, vol=20), pe, ts(15, 29, 40))
        rows = b.close_all()
        assert len(rows) == 2 and b.working_count() == 0
        assert {r["contract_id"] for r in rows} == {ce.contract_id, pe.contract_id}

    def test_multi_contract_independence(self, contracts):
        ce = contracts["NIFTY_20260728_24000_CE"]
        fut = contracts["NIFTY_20260728_FUT"]
        b = MinuteBuilder()
        b.add(tick(100, vol=10), ce, ts(9, 15, 1))
        b.add(tick(24010, vol=99), fut, ts(9, 15, 2))
        closed = b.add(tick(101, vol=12), ce, ts(9, 16, 1))
        assert len(closed) == 1 and closed[0]["contract_id"] == ce.contract_id
        assert b.working_count() == 2  # fut 09:15 still open + ce 09:16


class TestBarStore:
    @pytest.fixture()
    def store(self, tmp_path):
        s = BarStore(database_url=f"sqlite:///{tmp_path}/bars.db")
        yield s
        s.dispose()

    def _bar(self, contracts, minute_s=0):
        c = contracts["NIFTY_20260728_24000_CE"]
        b = MinuteBuilder()
        b.add(tick(100, vol=1000, oi=500, bid=99.5, ask=100.5, tbq=10, tsq=20), c, ts(9, 15 + minute_s, 1))
        return b.close_all()[0]

    def test_insert_and_count(self, store, contracts):
        assert store.insert_bars([self._bar(contracts)]) == 1
        assert store.bar_count() == 1

    def test_duplicate_insert_is_idempotent(self, store, contracts):
        bar = self._bar(contracts)
        store.insert_bars([bar])
        store.insert_bars([dict(bar)])  # replay the same minute
        assert store.bar_count() == 1

    def test_chain_snapshot_roundtrip(self, store):
        store.upsert_chain_snapshot({"spot": 24000.0, "contracts": {"X": {"ltp": 1.5}}})
        store.upsert_chain_snapshot({"spot": 24010.0, "contracts": {"X": {"ltp": 2.0}}})
        snap = store.read_chain_snapshot()
        assert snap["chain"]["spot"] == 24010.0

    def test_daily_session_upsert(self, store):
        store.upsert_daily_session(date(2026, 7, 28), {"bars_emitted": 10})
        store.upsert_daily_session(date(2026, 7, 28), {"bars_emitted": 32625})
        from sqlalchemy import select, text

        with store.engine.connect() as conn:
            rows = conn.execute(text("select stats from daily_sessions")).fetchall()
        assert len(rows) == 1
        assert json.loads(rows[0][0])["bars_emitted"] == 32625


class TestWorkerBarGlue:
    def test_on_ticks_closes_bars_and_drain_inserts(self, contracts, tmp_path, monkeypatch):
        from app.workers.options.worker import OptionsWorker
        from app.workers.options.state import ChainState

        worker = OptionsWorker()
        cs_list = list(contracts.values())
        worker.chain = ChainState(cs_list)
        worker.builder = MinuteBuilder()
        worker.recorder = __import__("app.workers.options.recorder", fromlist=["TickRecorder"]).TickRecorder(tmp_path)
        worker.bar_store = BarStore(database_url=f"sqlite:///{tmp_path}/glue.db")

        ce = contracts["NIFTY_20260728_24000_CE"]
        t1 = dict(tick(100, vol=1000), instrument_token=ce.instrument_token)
        t2 = dict(tick(101, vol=1200), instrument_token=ce.instrument_token)
        worker._on_ticks([t1], ts(9, 15, 1))
        worker._on_ticks([t2], ts(9, 16, 1))  # closes the 09:15 bar
        assert len(worker._pending_bars) == 1

        worker._drain_bars()
        assert worker.bars_inserted == 1
        assert worker.bar_store.bar_count() == 1
        assert worker._pending_bars == []
        worker.bar_store.dispose()
