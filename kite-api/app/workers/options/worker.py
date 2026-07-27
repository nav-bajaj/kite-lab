"""Options data worker — lifecycle skeleton (Phase 1).

Runs the market-clock state machine and the daily selection step. The
capture internals (websocket, state, aggregator, persistence) arrive in
Phases 2-3; their hooks are the _enter_*/_exit_* methods below.

Run locally:  python -m app.workers.options.worker
"""
from __future__ import annotations

import logging
import signal
import time
from datetime import date, datetime
from typing import Optional

from app.workers.options import instrument_loader
from app.workers.options.config import OptionsWorkerSettings, get_worker_settings
from app.workers.options.health import start_health_server
from app.workers.options.recorder import TickRecorder
from app.workers.options.scheduler import Phase, market_phase, now_ist
from app.workers.options.state import ChainState
from app.workers.options.subscriptions import SubscriptionManager

log = logging.getLogger("options_worker")


def _read_access_token() -> str:
    """Day token, kite_session (Postgres) first, access_token.txt fallback.

    On Railway the worker has no access to the web service's volume, so the
    DB row (mirrored by the daily login) is the only source. Locally the
    file usually exists and the DB may not — hence the fallback order:
    freshest wins when both exist."""
    from app.config import get_settings

    settings = get_settings()
    db_row = None
    try:
        from app.services.token_store import read_token

        db_row = read_token()
    except Exception as exc:
        log.debug("kite_session read unavailable: %s", exc)

    token_path = settings.data_dir / "access_token.txt"
    file_token = token_path.read_text().strip() if token_path.exists() else None

    if db_row and file_token:
        from datetime import timezone

        db_ts = db_row["updated_at"]
        if db_ts.tzinfo is None:  # SQLite drops tz; token_store writes UTC
            db_ts = db_ts.replace(tzinfo=timezone.utc)
        file_mtime = datetime.fromtimestamp(token_path.stat().st_mtime, tz=timezone.utc)
        return db_row["access_token"] if db_ts >= file_mtime else file_token
    if db_row:
        return db_row["access_token"]
    if file_token:
        return file_token
    raise FileNotFoundError("no access token in kite_session or access_token.txt")


def _kite_client():
    from kiteconnect import KiteConnect

    from app.config import get_settings

    kite = KiteConnect(api_key=get_settings().kite_api_key)
    kite.set_access_token(_read_access_token())
    return kite


class OptionsWorker:
    def __init__(self, settings: Optional[OptionsWorkerSettings] = None):
        self.settings = settings or get_worker_settings()
        self.phase: Phase = Phase.IDLE
        self.selection: Optional[instrument_loader.Selection] = None
        self.selection_date: Optional[date] = None
        self.started_at: datetime = now_ist()
        self.last_error: Optional[str] = None
        self._stop = False
        # capture stack, live only during CAPTURE
        self.chain: Optional[ChainState] = None
        self.subs: Optional[SubscriptionManager] = None
        self.ticker = None
        self.recorder: Optional[TickRecorder] = None
        self._nfo_rows = None  # the day's dump, kept for the widen universe
        self._last_flush: datetime = now_ist()
        self._last_heartbeat: datetime = now_ist()
        self._capture_started_at: Optional[datetime] = None

    # -- lifecycle ---------------------------------------------------------

    def run(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        signal.signal(signal.SIGTERM, self._handle_stop)
        signal.signal(signal.SIGINT, self._handle_stop)
        start_health_server(self, self.settings.health_port, self.settings.health_host)
        log.info("options worker up — health on :%d", self.settings.health_port)

        while not self._stop:
            try:
                self.tick(now_ist())
            except Exception:
                self.last_error = f"{now_ist().isoformat()} loop error"
                log.exception("worker loop error — continuing")
            time.sleep(self.settings.poll_seconds)
        log.info("options worker stopped")

    def tick(self, now: datetime) -> None:
        """One state-machine step. Split from run() so tests can drive it
        with a fixed clock and no sleeping."""
        new_phase = Phase.CAPTURE if self.settings.force_capture else market_phase(now)
        if new_phase != self.phase:
            log.info("phase %s -> %s", self.phase.value, new_phase.value)
            old_phase = self.phase
            # assign before the handlers: they can block (network), and the
            # health endpoint reads self.phase from another thread
            self.phase = new_phase
            self._on_transition(old_phase, new_phase, now)

        if self.phase == Phase.PRE_MARKET and self.selection_date != now.date():
            self._run_daily_selection(now)

        if self.phase == Phase.CAPTURE and self.recorder is not None:
            if (now - self._last_flush).total_seconds() >= self.settings.flush_seconds:
                self.recorder.flush()
                self._last_flush = now
                # One INFO line per flush window — remote log monitoring
                # (Railway logs are the only live view besides /admin)
                log.info(
                    "stats: ws=%s chain=%s recorder=%s",
                    self.ticker.counters() if self.ticker else None,
                    self.chain.counters() if self.chain else None,
                    self.recorder.counters(),
                )

        if (now - self._last_heartbeat).total_seconds() >= self.settings.heartbeat_seconds:
            self._last_heartbeat = now
            try:
                from app.services.worker_health_store import write_heartbeat

                write_heartbeat(self.phase.value, self.health_snapshot())
            except Exception as exc:
                log.debug("heartbeat skipped: %s", exc)

        if self.phase == Phase.CAPTURE and self.chain is not None:
            # KiteTicker reconnects on its own; this catches the cases it
            # can't fix — gave-up reconnects, dead tokens, or a client that
            # never started — by rebuilding with a freshly-read token.
            dead = self.ticker is None or (not self.ticker.connected and self._ticker_dead_for(now) > 60)
            if dead:
                log.warning("ticker dead — rebuilding client with fresh token")
                if self.ticker is not None:
                    self.ticker.stop()
                try:
                    self._start_ticker()
                except Exception as exc:
                    self.last_error = f"ticker restart failed: {exc}"
                    log.error("ticker restart failed (will retry): %s", exc)

    def _on_transition(self, old: Phase, new: Phase, now: datetime) -> None:
        if new == Phase.CAPTURE:
            self._enter_capture(now)
        elif old == Phase.CAPTURE:
            self._exit_capture(now)
        if new == Phase.EOD_FLUSH:
            self._enter_eod_flush(now)

    # -- daily selection ---------------------------------------------------

    def _run_daily_selection(self, now: datetime) -> None:
        try:
            kite = _kite_client()
            rows = instrument_loader.fetch_nfo_dump(kite)
            spot = instrument_loader.fetch_nifty_spot(kite)
        except Exception as exc:
            # Missing/expired token before 09:00 is expected some mornings;
            # keep retrying each poll until the login lands.
            self.last_error = f"selection fetch failed: {exc}"
            log.warning("daily selection fetch failed (will retry): %s", exc)
            return

        selection = instrument_loader.select_contracts(
            rows,
            spot_price=spot["price"],
            today=now.date(),
            strike_window=self.settings.strike_window,
            option_expiry_count=self.settings.option_expiries,
            future_expiry_count=self.settings.future_expiries,
            spot_row=spot["row"],
        )
        instrument_loader.save_dump(rows, self.settings.dump_dir / f"nfo_{now.date().isoformat()}.json")
        instrument_loader.save_selection(selection, self.settings.tokens_dir / f"{now.date().isoformat()}.json")
        self.selection = selection
        self.selection_date = now.date()
        self._nfo_rows = rows
        log.info("daily selection: %s", selection.summary())

    # -- capture -----------------------------------------------------------

    def _enter_capture(self, now: datetime) -> None:
        if self.selection is None:
            # Mid-session (re)start: recover the day's token list rather
            # than re-selecting off a moved spot.
            path = self.settings.tokens_dir / f"{now.date().isoformat()}.json"
            if path.exists():
                self.selection = instrument_loader.load_selection(path)
                self.selection_date = now.date()
                log.info("recovered selection: %s", self.selection.summary())
            else:
                log.warning("entering capture with no selection — running selection now")
                self._run_daily_selection(now)
        if self.selection is None:
            log.error("no selection — cannot start capture; will retry next poll")
            self.phase = Phase.IDLE  # forces re-entry attempt on the next tick
            return

        if self._nfo_rows is None:
            dump_path = self.settings.dump_dir / f"nfo_{now.date().isoformat()}.json"
            if dump_path.exists():
                self._nfo_rows = instrument_loader.load_dump(dump_path)

        self.chain = ChainState(self.selection.contracts)
        self.subs = SubscriptionManager(
            self.selection,
            self._nfo_rows or [],
            strike_window=self.settings.strike_window,
            drift_strikes=self.settings.recenter_drift_strikes,
        )
        self.recorder = TickRecorder(self.settings.ticks_dir)
        self._capture_started_at = now
        self._start_ticker()
        log.info("capture start: %d contracts", len(self.selection.contracts))

    def _start_ticker(self) -> None:
        from app.config import get_settings
        from app.workers.options.websocket import TickerClient

        self.ticker = TickerClient(
            api_key=get_settings().kite_api_key,
            access_token=_read_access_token(),
            tokens=self.subs.tokens(),
            on_ticks=self._on_ticks,
        )
        self._capture_started_at = now_ist()  # grace window for the new client
        self.ticker.start()

    def _on_ticks(self, ticks, recv_ts: datetime) -> None:
        """Ticker-thread callback — keep it allocation-light and lock-safe."""
        widen: list = []
        for tick in ticks:
            cs = self.chain.apply_tick(tick, recv_ts)
            if cs is None:
                continue
            self.recorder.add(tick, cs.contract, recv_ts)
            if cs.contract.kind == "SPOT" and self.subs:
                widen = self.subs.on_spot(cs.ltp) or widen
        if widen:
            self.chain.register(widen)
            self.ticker.subscribe_more([c.instrument_token for c in widen])
            instrument_loader.save_selection(
                self.selection, self.settings.tokens_dir / f"{self.selection.trade_date.isoformat()}.json"
            )

    def _exit_capture(self, now: datetime) -> None:
        if self.ticker:
            self.ticker.stop()
            self.ticker = None
        if self.recorder:
            self.recorder.flush()
        log.info("capture stop")

    def _enter_eod_flush(self, now: datetime) -> None:
        if self.recorder:
            self.recorder.flush()
            log.info("eod: recorder %s", self.recorder.counters())
        log.info("eod flush (aggregator/persistence land in Phase 3)")

    # -- health ------------------------------------------------------------

    def health_snapshot(self) -> dict:
        snap = {
            "phase": self.phase.value,
            "started_at": self.started_at.isoformat(),
            "now": now_ist().isoformat(),
            "selection_date": self.selection_date.isoformat() if self.selection_date else None,
            "contracts": len(self.selection.contracts) if self.selection else 0,
            "atm_strike": self.selection.atm_strike if self.selection else None,
            "last_error": self.last_error,
        }
        if self.ticker:
            snap["ws"] = self.ticker.counters()
        if self.chain:
            snap["chain"] = self.chain.counters()
            snap["staleness_seconds"] = self.chain.staleness_seconds(now_ist())
        if self.recorder:
            snap["recorder"] = self.recorder.counters()
        if self.subs:
            snap["widen_events"] = self.subs.widen_events
        return snap

    def _ticker_dead_for(self, now: datetime) -> float:
        """Seconds since the ticker last looked alive (tick or connect)."""
        last = self.ticker.last_tick_at
        if last is None:
            last = self._capture_started_at or now
        return (now - last).total_seconds()

    def _handle_stop(self, signum, frame) -> None:
        log.info("signal %s — stopping", signum)
        self._stop = True


if __name__ == "__main__":
    OptionsWorker().run()
