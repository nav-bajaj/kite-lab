"""Options worker Phase 2: chain state, widen-only subscriptions, recorder.

Two data sources:
- tests/fixtures/nfo_nifty_2026-07-27.json.gz — a REAL recorded NIFTY NFO
  dump (captured 2026-07-27, spot 23995.95). Selection facts asserted here
  (ATM 24000, expiries 07-28/08-04, futures 07-28/08-25) are real.
- Tick dicts are SYNTHETIC — they mirror kiteconnect FULL-mode tick shape
  but the prices/quantities are invented. Replace with recorded ticks once
  a live session is captured.
"""
import gzip
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from app.services.market_service import IST
from app.workers.options import instrument_loader as il
from app.workers.options.recorder import TickRecorder, flatten_tick
from app.workers.options.state import ChainState
from app.workers.options.subscriptions import SubscriptionManager

FIXTURE = Path(__file__).parent / "fixtures" / "nfo_nifty_2026-07-27.json.gz"
FIXTURE_DATE = date(2026, 7, 27)
FIXTURE_SPOT = 23995.95


def load_real_dump():
    with gzip.open(FIXTURE, "rb") as f:
        return il.normalize_rows(json.loads(f.read()))


@pytest.fixture(scope="module")
def real_rows():
    return load_real_dump()


@pytest.fixture()
def selection(real_rows):
    return il.select_contracts(real_rows, spot_price=FIXTURE_SPOT, today=FIXTURE_DATE)


def make_tick(token, ltp, with_depth=True, oi=0, volume=0, exch_ts=None):
    tick = {
        "tradable": True,
        "mode": "full",
        "instrument_token": token,
        "last_price": ltp,
        "last_traded_quantity": 75,
        "volume_traded": volume,
        "total_buy_quantity": 1000,
        "total_sell_quantity": 900,
        "oi": oi,
        "oi_day_high": oi,
        "oi_day_low": max(oi - 100, 0),
        "exchange_timestamp": exch_ts or datetime(2026, 7, 27, 10, 0, 0),
    }
    if with_depth:
        tick["depth"] = {
            "buy": [{"price": ltp - 0.5 * (i + 1), "quantity": 100 * (i + 1), "orders": i + 1} for i in range(5)],
            "sell": [{"price": ltp + 0.5 * (i + 1), "quantity": 110 * (i + 1), "orders": i + 1} for i in range(5)],
        }
    return tick


class TestRealDumpSelection:
    def test_recorded_dump_selects_as_on_capture_day(self, selection):
        assert selection.atm_strike == 24000
        assert selection.strike_step == 50
        assert [d.isoformat() for d in selection.option_expiries] == ["2026-07-28", "2026-08-04"]
        assert [d.isoformat() for d in selection.future_expiries] == ["2026-07-28", "2026-08-25"]
        kinds = {}
        for c in selection.contracts:
            kinds[c.kind] = kinds.get(c.kind, 0) + 1
        assert kinds == {"SPOT": 1, "FUT": 2, "CE": 42, "PE": 42}


class TestChainState:
    def test_option_tick_updates_all_fields(self, selection):
        chain = ChainState(selection.contracts)
        atm_ce = chain.by_id["NIFTY_20260728_24000_CE"]
        recv = IST.localize(datetime(2026, 7, 27, 10, 0, 1))
        cs = chain.apply_tick(make_tick(atm_ce.contract.instrument_token, 145.5, oi=50000, volume=12000), recv)
        assert cs is atm_ce
        assert cs.ltp == 145.5
        assert cs.oi == 50000
        assert cs.best_bid == 145.0
        assert cs.best_ask == 146.0
        assert cs.spread == pytest.approx(1.0)
        assert len(cs.bids) == 5 and len(cs.asks) == 5
        assert cs.recv_ts == recv

    def test_spot_tick_without_depth_updates_spot_price(self, selection):
        chain = ChainState(selection.contracts)
        spot_token = chain.by_id["NIFTY_SPOT"].contract.instrument_token
        recv = IST.localize(datetime(2026, 7, 27, 10, 0, 1))
        chain.apply_tick(make_tick(spot_token, 24050.10, with_depth=False), recv)
        assert chain.spot_price == 24050.10
        assert chain.by_id["NIFTY_SPOT"].bids == []

    def test_unknown_token_ignored(self, selection):
        chain = ChainState(selection.contracts)
        assert chain.apply_tick(make_tick(999999999, 1.0), IST.localize(datetime(2026, 7, 27, 10, 0))) is None

    def test_staleness_and_counters(self, selection):
        chain = ChainState(selection.contracts)
        t0 = IST.localize(datetime(2026, 7, 27, 10, 0, 0))
        spot_token = chain.by_id["NIFTY_SPOT"].contract.instrument_token
        chain.apply_tick(make_tick(spot_token, 24000, with_depth=False), t0)
        t1 = IST.localize(datetime(2026, 7, 27, 10, 0, 7))
        assert chain.staleness_seconds(t1) == pytest.approx(7.0)
        c = chain.counters()
        assert c["contracts"] == 87 and c["contracts_ticked"] == 1 and c["total_ticks"] == 1

    def test_chain_view_pairs_ce_pe(self, selection):
        chain = ChainState(selection.contracts)
        view = chain.chain_view()
        near = view[date(2026, 7, 28)]
        assert set(near[24000.0].keys()) == {"CE", "PE"}
        assert len(near) == 21


class TestWidenOnlyIntraday:
    def _mgr(self, selection, real_rows):
        return SubscriptionManager(selection, real_rows, strike_window=10, drift_strikes=2)

    def test_below_threshold_no_op(self, selection, real_rows):
        mgr = self._mgr(selection, real_rows)
        assert mgr.on_spot(24049.0) == []  # nearest 24050, drift 1 strike < 2

    def test_drift_triggers_additions_both_expiries(self, selection, real_rows):
        mgr = self._mgr(selection, real_rows)
        before = len(selection.contracts)
        additions = mgr.on_spot(24101.0)  # nearest 24100 — 2 strikes up
        assert additions
        assert {c.kind for c in additions} == {"CE", "PE"}
        assert {c.expiry for c in additions} == set(selection.option_expiries)
        new_strikes = {c.strike for c in additions}
        assert new_strikes == {24550.0, 24600.0}
        assert len(selection.contracts) == before + len(additions)
        assert mgr.widen_events == 1

    def test_widen_is_idempotent_at_same_level(self, selection, real_rows):
        mgr = self._mgr(selection, real_rows)
        mgr.on_spot(24101.0)
        assert mgr.on_spot(24101.0) == []
        assert mgr.on_spot(24120.0) == []  # still nearest 24100

    def test_never_removes_strikes(self, selection, real_rows):
        mgr = self._mgr(selection, real_rows)
        near = selection.option_expiries[0]
        before = set(mgr.subscribed_strikes[near])
        mgr.on_spot(24101.0)
        mgr.on_spot(23899.0)  # drift back down
        assert before <= set(mgr.subscribed_strikes[near])


class TestRecorder:
    def test_flatten_depth_and_missing_depth(self, selection):
        chain = ChainState(selection.contracts)
        atm = chain.by_id["NIFTY_20260728_24000_CE"]
        recv = IST.localize(datetime(2026, 7, 27, 10, 0, 1))
        row = flatten_tick(make_tick(atm.contract.instrument_token, 145.5, oi=50000), atm.contract, recv)
        assert row["contract_id"] == "NIFTY_20260728_24000_CE"
        assert row["bid1_price"] == 145.0 and row["ask5_qty"] == 550
        spot = chain.by_id["NIFTY_SPOT"]
        row2 = flatten_tick(make_tick(spot.contract.instrument_token, 24000, with_depth=False), spot.contract, recv)
        assert row2["bid1_price"] == 0.0 and row2["ask5_orders"] == 0

    def test_flush_writes_readable_parquet(self, selection, tmp_path):
        import pandas as pd

        chain = ChainState(selection.contracts)
        atm = chain.by_id["NIFTY_20260728_24000_CE"]
        rec = TickRecorder(tmp_path, flush_rows=10)
        recv = IST.localize(datetime(2026, 7, 27, 10, 0, 1))
        for i in range(25):
            rec.add(make_tick(atm.contract.instrument_token, 145.0 + i), atm.contract, recv)
        rec.flush()
        files = list(tmp_path.rglob("*.parquet"))
        assert files and files[0].parent.name == "date=2026-07-27"
        df = pd.concat(pd.read_parquet(f) for f in files)
        assert len(df) == 25
        assert "bid5_orders" in df.columns and "oi" in df.columns
        assert rec.counters()["rows_written"] == 25 and rec.counters()["buffered"] == 0


class TestWorkerOnTicksGlue:
    def test_spot_drift_widens_chain_and_resubscribes(self, selection, real_rows, tmp_path, monkeypatch):
        from app.workers.options.worker import OptionsWorker

        worker = OptionsWorker()
        worker.selection = selection
        worker.selection_date = FIXTURE_DATE
        worker.chain = ChainState(selection.contracts)
        worker.subs = SubscriptionManager(selection, real_rows, 10, 2)
        worker.recorder = TickRecorder(tmp_path)

        subscribed = []

        class StubTicker:
            def subscribe_more(self, tokens):
                subscribed.extend(tokens)

        worker.ticker = StubTicker()
        monkeypatch.setattr(worker.settings.__class__, "tokens_dir", property(lambda self: tmp_path / "tokens"))

        spot_token = worker.chain.by_id["NIFTY_SPOT"].contract.instrument_token
        recv = IST.localize(datetime(2026, 7, 27, 10, 0, 1))
        worker._on_ticks([make_tick(spot_token, 24101.0, with_depth=False)], recv)

        assert subscribed, "widen must push new tokens to the live subscription"
        for t in subscribed:
            assert t in worker.chain.by_token, "widened contracts must be registered in chain state"
        saved = il.load_selection(tmp_path / "tokens" / "2026-07-27.json")
        assert len(saved.contracts) == len(selection.contracts)
