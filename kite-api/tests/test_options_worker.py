"""Options worker Phase 1: instrument selection + market-clock phases.

The NFO dump used here is SYNTHETIC (built by _build_nfo_dump below) — it
mirrors the shape of kite.instruments("NFO") rows but the tokens, lot
sizes, and expiry dates are invented for the test. Replace/augment with a
recorded real dump once one is captured (Phase 2 soak).
"""
from datetime import date, datetime, timedelta

import pytest

from app.services.market_service import IST
from app.workers.options import instrument_loader as il
from app.workers.options.scheduler import Phase, market_phase

TODAY = date(2026, 7, 27)  # Monday, not an NSE holiday
NEAR_EXPIRY = date(2026, 7, 30)   # Thursday
NEXT_EXPIRY = date(2026, 8, 6)    # Thursday
FAR_EXPIRY = date(2026, 9, 24)    # must be excluded
FUT_NEAR = date(2026, 7, 30)
FUT_NEXT = date(2026, 8, 27)
FUT_FAR = date(2026, 9, 24)


def _strike_grid():
    # NIFTY-like uneven grid: 100-step wings, 50-step body
    return (
        list(range(23000, 24000, 100))
        + list(range(24000, 26050, 50))
        + list(range(26100, 27100, 100))
    )


def _build_nfo_dump():
    rows = []
    token = 1000
    for expiry in (NEAR_EXPIRY, NEXT_EXPIRY, FAR_EXPIRY):
        for strike in _strike_grid():
            for opt_type in ("CE", "PE"):
                token += 1
                rows.append({
                    "instrument_token": token,
                    "tradingsymbol": f"NIFTY{expiry:%y%m%d}{strike}{opt_type}",
                    "name": "NIFTY",
                    "expiry": expiry.isoformat(),  # JSON dumps carry strings
                    "strike": strike,
                    "tick_size": 0.05,
                    "lot_size": 75,
                    "instrument_type": opt_type,
                    "segment": "NFO-OPT",
                    "exchange": "NFO",
                })
    for expiry in (FUT_NEAR, FUT_NEXT, FUT_FAR):
        token += 1
        rows.append({
            "instrument_token": token,
            "tradingsymbol": f"NIFTY{expiry:%y%b}FUT".upper(),
            "name": "NIFTY",
            "expiry": expiry.isoformat(),
            "strike": 0,
            "tick_size": 0.05,
            "lot_size": 75,
            "instrument_type": "FUT",
            "segment": "NFO-FUT",
            "exchange": "NFO",
        })
    # noise that must be filtered out
    token += 1
    rows.append({
        "instrument_token": token,
        "tradingsymbol": "BANKNIFTY26073055000CE",
        "name": "BANKNIFTY",
        "expiry": NEAR_EXPIRY.isoformat(),
        "strike": 55000,
        "tick_size": 0.05,
        "lot_size": 30,
        "instrument_type": "CE",
        "segment": "NFO-OPT",
        "exchange": "NFO",
    })
    return rows


@pytest.fixture()
def dump():
    return _build_nfo_dump()


class TestSelection:
    def test_counts_atm_and_expiries(self, dump):
        sel = il.select_contracts(dump, spot_price=25012.4, today=TODAY)
        assert sel.atm_strike == 25000
        assert sel.strike_step == 50
        assert sel.option_expiries == [NEAR_EXPIRY, NEXT_EXPIRY]
        assert sel.future_expiries == [FUT_NEAR, FUT_NEXT]
        kinds = {}
        for c in sel.contracts:
            kinds[c.kind] = kinds.get(c.kind, 0) + 1
        # 21 strikes x CE/PE x 2 expiries + 2 futures + spot
        assert kinds == {"CE": 42, "PE": 42, "FUT": 2, "SPOT": 1}
        assert len(sel.contracts) == 87
        assert len(set(sel.tokens)) == 87

    def test_atm_rounds_to_nearest_grid_strike(self, dump):
        assert il.select_contracts(dump, 25026.0, TODAY).atm_strike == 25050
        assert il.select_contracts(dump, 24975.1, TODAY).atm_strike == 25000
        assert il.select_contracts(dump, 24974.9, TODAY).atm_strike == 24950

    def test_window_strikes_are_contiguous_grid_positions(self, dump):
        sel = il.select_contracts(dump, 25012.4, TODAY)
        strikes = sorted({c.strike for c in sel.contracts if c.kind == "CE" and c.expiry == NEAR_EXPIRY})
        assert strikes == [24500 + 50 * i for i in range(21)]

    def test_uneven_grid_uses_positions_not_price_arithmetic(self, dump):
        # ATM at the body/wing boundary: upper side must step 100s, and the
        # window must still be 10 strikes each side by position.
        sel = il.select_contracts(dump, 26010.0, TODAY)
        assert sel.atm_strike == 26000
        strikes = sorted({c.strike for c in sel.contracts if c.kind == "PE" and c.expiry == NEAR_EXPIRY})
        assert len(strikes) == 21
        assert strikes[-1] == 27000  # 10 positions above 26000 in 100-steps
        assert strikes[0] == 25500   # 10 positions below in 50-steps

    def test_excludes_far_expiry_and_other_underlyings(self, dump):
        sel = il.select_contracts(dump, 25012.4, TODAY)
        assert all(c.expiry != FAR_EXPIRY for c in sel.contracts)
        assert all("BANKNIFTY" not in c.tradingsymbol for c in sel.contracts)

    def test_contract_ids(self, dump):
        sel = il.select_contracts(dump, 25012.4, TODAY)
        ids = {c.contract_id for c in sel.contracts}
        assert "NIFTY_20260730_25000_CE" in ids
        assert "NIFTY_20260806_24500_PE" in ids
        assert "NIFTY_20260730_FUT" in ids
        assert "NIFTY_SPOT" in ids
        assert len(ids) == len(sel.contracts)

    def test_spot_row_token_preferred_over_fallback(self, dump):
        sel = il.select_contracts(dump, 25012.4, TODAY, spot_row={"instrument_token": 999999})
        spot = [c for c in sel.contracts if c.kind == "SPOT"][0]
        assert spot.instrument_token == 999999


class TestWidenOnly:
    def test_drift_up_adds_only_new_upper_strikes(self):
        grid = [24000 + 50 * i for i in range(41)]  # 24000..26000
        current = il.window_strikes(grid, 25000, 10)  # 24500..25500
        added = il.strikes_to_add(current, grid, 25150, 10)
        assert added == [25550, 25600, 25650]

    def test_no_drift_adds_nothing(self):
        grid = [24000 + 50 * i for i in range(41)]
        current = il.window_strikes(grid, 25000, 10)
        assert il.strikes_to_add(current, grid, 25000, 10) == []

    def test_never_removes(self):
        grid = [24000 + 50 * i for i in range(41)]
        current = il.window_strikes(grid, 25000, 10)
        added = il.strikes_to_add(current, grid, 24800, 10)
        assert set(added).isdisjoint(current)


class TestPersistenceRoundtrips:
    def test_selection_roundtrip(self, dump, tmp_path):
        sel = il.select_contracts(dump, 25012.4, TODAY)
        path = tmp_path / "tokens" / "2026-07-27.json"
        il.save_selection(sel, path)
        loaded = il.load_selection(path)
        assert loaded.atm_strike == sel.atm_strike
        assert loaded.option_expiries == sel.option_expiries
        assert [c.contract_id for c in loaded.contracts] == [c.contract_id for c in sel.contracts]

    def test_dump_roundtrip_parses_dates(self, dump, tmp_path):
        path = tmp_path / "nfo.json"
        il.save_dump(il.normalize_rows(dump), path)
        loaded = il.load_dump(path)
        assert loaded[0]["expiry"] == NEAR_EXPIRY
        assert isinstance(loaded[0]["strike"], float)


class TestMarketPhase:
    def _at(self, d, h, m):
        return IST.localize(datetime(d.year, d.month, d.day, h, m))

    def test_trading_day_phases(self):
        d = TODAY
        assert market_phase(self._at(d, 8, 0)) == Phase.IDLE
        assert market_phase(self._at(d, 8, 30)) == Phase.PRE_MARKET
        assert market_phase(self._at(d, 9, 14)) == Phase.PRE_MARKET
        assert market_phase(self._at(d, 9, 15)) == Phase.CAPTURE
        assert market_phase(self._at(d, 15, 29)) == Phase.CAPTURE
        assert market_phase(self._at(d, 15, 30)) == Phase.EOD_FLUSH
        assert market_phase(self._at(d, 15, 59)) == Phase.EOD_FLUSH
        assert market_phase(self._at(d, 16, 0)) == Phase.IDLE

    def test_weekend_and_holiday_idle(self):
        saturday = date(2026, 7, 25)
        republic_day = date(2026, 1, 26)  # Monday, NSE holiday
        assert market_phase(self._at(saturday, 10, 0)) == Phase.IDLE
        assert market_phase(self._at(republic_day, 10, 0)) == Phase.IDLE

    def test_naive_datetime_treated_as_ist(self):
        assert market_phase(datetime(2026, 7, 27, 10, 0)) == Phase.CAPTURE


class TestWorkerLifecycle:
    def test_tick_transitions_and_selects_once(self, monkeypatch, dump):
        from app.workers.options.worker import OptionsWorker

        worker = OptionsWorker()
        calls = []

        def fake_selection(now):
            calls.append(now)
            worker.selection = il.select_contracts(dump, 25012.4, now.date())
            worker.selection_date = now.date()

        monkeypatch.setattr(worker, "_run_daily_selection", fake_selection)

        d = TODAY
        at = lambda h, m: IST.localize(datetime(d.year, d.month, d.day, h, m))
        worker.tick(at(8, 0))
        assert worker.phase == Phase.IDLE and calls == []
        worker.tick(at(8, 46))
        worker.tick(at(8, 50))
        assert worker.phase == Phase.PRE_MARKET
        assert len(calls) == 1  # selection ran once, not per poll
        worker.tick(at(9, 20))
        assert worker.phase == Phase.CAPTURE
        worker.tick(at(15, 45))
        assert worker.phase == Phase.EOD_FLUSH
        worker.tick(at(16, 30))
        assert worker.phase == Phase.IDLE
        snap = worker.health_snapshot()
        assert snap["contracts"] == 87
        assert snap["selection_date"] == d.isoformat()
