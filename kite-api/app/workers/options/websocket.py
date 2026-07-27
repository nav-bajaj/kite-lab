"""KiteTicker wrapper — the only module that talks to the wire.

Business logic stays out: this class connects, subscribes FULL mode,
re-subscribes after KiteTicker's built-in auto-reconnect, exposes
counters, and hands raw tick dicts to a callback. Everything it calls
back into must be thread-safe (ticks arrive on the ticker's thread).
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Callable, List, Optional

from app.services.market_service import IST

log = logging.getLogger("options_worker.ws")


class TickerClient:
    def __init__(
        self,
        api_key: str,
        access_token: str,
        tokens: List[int],
        on_ticks: Callable[[List[dict], datetime], None],
    ):
        from kiteconnect import KiteTicker

        self._on_ticks_cb = on_ticks
        self._tokens = list(tokens)
        self._lock = threading.Lock()
        self.packets = 0
        self.reconnects = 0
        self.last_tick_at: Optional[datetime] = None
        self.connected = False
        self.last_error: Optional[str] = None

        self.ws = KiteTicker(api_key, access_token)
        self.ws.on_connect = self._handle_connect
        self.ws.on_ticks = self._handle_ticks
        self.ws.on_close = self._handle_close
        self.ws.on_error = self._handle_error
        self.ws.on_reconnect = self._handle_reconnect
        self.ws.on_noreconnect = self._handle_noreconnect

    # -- public ------------------------------------------------------------

    def start(self) -> None:
        # threaded=True: KiteTicker runs its own reactor thread and manages
        # reconnection with exponential backoff internally.
        self.ws.connect(threaded=True)

    def stop(self) -> None:
        try:
            self.ws.close()
        except Exception:
            log.exception("error closing websocket")
        self.connected = False

    def subscribe_more(self, tokens: List[int]) -> None:
        """Intraday widen: add tokens to the live subscription."""
        with self._lock:
            new = [t for t in tokens if t not in self._tokens]
            self._tokens.extend(new)
        if new and self.connected:
            self.ws.subscribe(new)
            self.ws.set_mode(self.ws.MODE_FULL, new)
            log.info("subscribed %d additional tokens (total %d)", len(new), len(self._tokens))

    def counters(self) -> dict:
        return {
            "connected": self.connected,
            "packets": self.packets,
            "reconnects": self.reconnects,
            "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
            "subscribed": len(self._tokens),
            "last_error": self.last_error,
        }

    # -- ticker callbacks (ticker thread) ----------------------------------

    def _handle_connect(self, ws, response) -> None:
        self.connected = True
        with self._lock:
            tokens = list(self._tokens)
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)
        log.info("ws connected — subscribed %d tokens FULL", len(tokens))

    def _handle_ticks(self, ws, ticks) -> None:
        recv_ts = datetime.now(IST)
        self.packets += 1
        self.last_tick_at = recv_ts
        try:
            self._on_ticks_cb(ticks, recv_ts)
        except Exception:
            log.exception("on_ticks callback failed — feed continues")

    def _handle_close(self, ws, code, reason) -> None:
        self.connected = False
        log.warning("ws closed: %s %s", code, reason)

    def _handle_error(self, ws, code, reason) -> None:
        self.last_error = f"{code} {reason}"
        log.error("ws error: %s %s", code, reason)

    def _handle_reconnect(self, ws, attempts_count) -> None:
        self.reconnects += 1
        log.warning("ws reconnecting (attempt %d) — gap in feed", attempts_count)

    def _handle_noreconnect(self, ws) -> None:
        self.connected = False
        self.last_error = "gave up reconnecting"
        log.error("ws gave up reconnecting — worker loop will restart the client")
