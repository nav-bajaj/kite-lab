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

import threading

from app.workers.options import instrument_loader
from app.workers.options.aggregator import MinuteBuilder
from app.workers.options.config import OptionsWorkerSettings, get_worker_settings
from app.workers.options.health import start_health_server
from app.workers.options.recorder import TickRecorder
from app.workers.options.scheduler import Phase, market_phase, now_ist
from app.workers.options.state import ChainState
from app.workers.options.subscriptions import SubscriptionManager

log = logging.getLogger("options_worker")


def _read_credentials() -> "tuple[str, str]":
    """(api_key, access_token) — kite_session (Postgres) first,
    access_token.txt fallback, freshest wins when both exist.

    A token only validates under the Kite app key that generated it, and
    logins happen from environments holding different apps (local .env vs
    the Railway web service) — so the DB row carries its api_key and the
    pair is used together. File fallback pairs with the env's own key."""
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

    def _from_db():
        return (db_row.get("api_key") or settings.kite_api_key, db_row["access_token"])

    if db_row and file_token:
        from datetime import timezone

        db_ts = db_row["updated_at"]
        if db_ts.tzinfo is None:  # SQLite drops tz; token_store writes UTC
            db_ts = db_ts.replace(tzinfo=timezone.utc)
        file_mtime = datetime.fromtimestamp(token_path.stat().st_mtime, tz=timezone.utc)
        return _from_db() if db_ts >= file_mtime else (settings.kite_api_key, file_token)
    if db_row:
        return _from_db()
    if file_token:
        return (settings.kite_api_key, file_token)
    raise FileNotFoundError("no access token in kite_session or access_token.txt")


def _kite_client():
    from kiteconnect import KiteConnect

    api_key, token = _read_credentials()
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(token)
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
        self.builder: Optional[MinuteBuilder] = None
        self.bar_store = None
        self._pending_bars: list = []
        self._bars_lock = threading.Lock()
        self.bars_inserted = 0
        self.db_errors = 0
        self._last_snapshot: datetime = now_ist()
        self._nfo_rows = None  # the day's dump, kept for the widen universe
        self._last_flush: datetime = now_ist()
        self._last_heartbeat: datetime = now_ist()
        self._capture_started_at: Optional[datetime] = None
        self._selection_failures = 0

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

        if self.phase == Phase.CAPTURE:
            self._drain_bars()
            if self.chain is not None and self.bar_store is not None:
                if (now - self._last_snapshot).total_seconds() >= self.settings.snapshot_seconds:
                    self._last_snapshot = now
                    try:
                        self.bar_store.upsert_chain_snapshot(self.chain.snapshot_payload())
                    except Exception as exc:
                        self.db_errors += 1
                        log.warning("snapshot upsert failed: %s", exc)

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
            # Auth failures right after 08:30 are EXPECTED — selection
            # retries start at the same moment the morning login job does,
            # and lose the race for a few seconds. Only surface last_error
            # (which turns the /admin dot red) once failures persist past
            # the grace window; before that, log quietly and retry.
            self._selection_failures += 1
            if self._selection_failures > self.settings.selection_error_grace_polls:
                self.last_error = f"selection fetch failed: {exc}"
                log.warning("daily selection fetch failed (attempt %d): %s", self._selection_failures, exc)
            else:
                log.info("selection waiting on morning token (attempt %d): %s", self._selection_failures, exc)
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
        # success supersedes any transient morning failure
        self._selection_failures = 0
        self.last_error = None
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
        self.builder = MinuteBuilder()
        self._init_bar_store()
        self._capture_started_at = now
        self._start_ticker()
        log.info("capture start: %d contracts", len(self.selection.contracts))

    def _init_bar_store(self) -> None:
        """DB persistence is additive: raw Parquet is the safety net, so a
        down database must never block capture. Retried from the loop."""
        try:
            from app.workers.options.bar_store import BarStore

            self.bar_store = BarStore()
        except Exception as exc:
            self.bar_store = None
            self.db_errors += 1
            log.warning("bar store unavailable (capture continues, will retry): %s", exc)

    def _start_ticker(self) -> None:
        from app.workers.options.websocket import TickerClient

        api_key, token = _read_credentials()
        self.ticker = TickerClient(
            api_key=api_key,
            access_token=token,
            tokens=self.subs.tokens(),
            on_ticks=self._on_ticks,
        )
        self._capture_started_at = now_ist()  # grace window for the new client
        self.ticker.start()

    def _on_ticks(self, ticks, recv_ts: datetime) -> None:
        """Ticker-thread callback — keep it allocation-light and lock-safe.
        Bars close here but INSERT on the worker loop, never this thread."""
        widen: list = []
        closed: list = []
        for tick in ticks:
            cs = self.chain.apply_tick(tick, recv_ts)
            if cs is None:
                continue
            self.recorder.add(tick, cs.contract, recv_ts)
            if self.builder is not None:
                closed.extend(self.builder.add(tick, cs.contract, recv_ts))
            if cs.contract.kind == "SPOT" and self.subs:
                widen = self.subs.on_spot(cs.ltp) or widen
        if closed:
            with self._bars_lock:
                self._pending_bars.extend(closed)
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
        if self.builder is not None:
            with self._bars_lock:
                self._pending_bars.extend(self.builder.close_all())
            self._drain_bars()
            log.info("eod: bars emitted=%d inserted=%d db_errors=%d",
                     self.builder.bars_emitted, self.bars_inserted, self.db_errors)
        if self.bar_store is not None:
            try:
                self.bar_store.upsert_daily_session(now.date(), self._session_stats(now))
            except Exception as exc:
                self.db_errors += 1
                log.warning("daily_sessions write failed: %s", exc)
        self._materialize_greeks(now)
        self._archive_ticks(now)
        self._write_daily_report(now)

    def _write_daily_report(self, now: datetime) -> None:
        """EOD: render the analytics digest to the volume. Best-effort."""
        try:
            from app.microstructure.daily_report import generate

            md = generate(now.date().isoformat())
            report_dir = self.settings.options_data_dir / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / f"{now.date().isoformat()}.md").write_text(md)
            log.info("eod: daily report written (%d chars)", len(md))
        except Exception as exc:
            log.warning("daily report failed (rerun via daily_report CLI): %s", exc)

    def _archive_ticks(self, now: datetime) -> None:
        """EOD: compress + prune old raw-tick days (Phase 5 retention).
        Best-effort — a failure leaves raw data in place, never the
        other way around."""
        try:
            from app.workers.options.archive import archive_old_days

            stats = archive_old_days(
                self.settings.ticks_dir,
                self.settings.ticks_archive_dir,
                self.settings.keep_raw_days,
                now.date(),
            )
            if any(stats.values()):
                log.info("eod: tick archive %s", stats)
        except Exception as exc:
            log.warning("tick archival failed (raw data untouched): %s", exc)

    def _materialize_greeks(self, now: datetime) -> None:
        """EOD: derive IV/Greeks for the day's bars (microstructure Stage 1).
        Analytics must never take the capture path down — best-effort."""
        try:
            from app.microstructure.materialize import run as materialize_run

            n = materialize_run(days=[now.date().isoformat()])
            log.info("eod: greeks materialized for %s (%d rows)", now.date(), n)
        except Exception as exc:
            log.warning("greeks materialization failed (bars are safe, rerun manually): %s", exc)

    def _session_stats(self, now: datetime) -> dict:
        return {
            "selection": self.selection.summary() if self.selection else None,
            "ws": self.ticker.counters() if self.ticker else None,
            "chain": self.chain.counters() if self.chain else None,
            "recorder": self.recorder.counters() if self.recorder else None,
            "bars_emitted": self.builder.bars_emitted if self.builder else 0,
            "bars_inserted": self.bars_inserted,
            "db_errors": self.db_errors,
            "widen_events": self.subs.widen_events if self.subs else 0,
            "closed_at": now.isoformat(),
        }

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
        if self.builder is not None:
            with self._bars_lock:
                pending = len(self._pending_bars)
            snap["bars"] = {
                "emitted": self.builder.bars_emitted,
                "inserted": self.bars_inserted,
                "pending": pending,
                "db_errors": self.db_errors,
            }
        return snap

    def _drain_bars(self) -> None:
        """Move closed bars from the ticker-thread buffer into Postgres.
        On DB failure the rows go back to the buffer (bounded — the raw
        Parquet is the authoritative recovery source, not this buffer)."""
        with self._bars_lock:
            if not self._pending_bars:
                return
            rows, self._pending_bars = self._pending_bars, []
        if self.bar_store is None:
            self._init_bar_store()
        if self.bar_store is None:
            self._requeue(rows)
            return
        try:
            self.bars_inserted += self.bar_store.insert_bars(rows)
        except Exception as exc:
            self.db_errors += 1
            log.warning("bar insert failed (%d rows requeued): %s", len(rows), exc)
            self._requeue(rows)

    def _requeue(self, rows: list) -> None:
        with self._bars_lock:
            self._pending_bars = (rows + self._pending_bars)[:50_000]

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
