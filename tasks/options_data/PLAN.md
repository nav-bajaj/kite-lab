# Options Data Capture — Plan

> Day-1 plan per `tasks/CONVENTIONS.md`. First step of the options initiative
> for Marketworks: capture live NIFTY F&O data (futures, options chain, market
> depth, OI) that the historical API can't give us, so we can later study
> whether depth/OI have any bearing on order flow and short-term moves.

## Why

Zerodha's `historical_data` has **no market depth**, limited OI, needs the
add-on, and is rate-limited. Depth history essentially doesn't exist unless we
record it ourselves. So we stream it live and store it.

## What Kite gives us (confirmed against the existing REST usage)

- **Instrument master** `kite.instruments("NFO")` — every NIFTY FUT + option
  strike with `instrument_token`, `tradingsymbol`, `expiry`, `strike`,
  `instrument_type` (FUT/CE/PE), `lot_size`. (Same dump pattern as
  `scripts/cache_instruments.py`, filtered to NFO / name == NIFTY.)
- **`KiteTicker` FULL mode** (WebSocket) — real-time LTP, volume, **OI**,
  OHLC, and **5-level market depth**, pushed on change, no per-request rate
  limit, ~3000 instruments/connection. This is the capture source.
- (`kite.quote()` REST also returns depth+oi but is ~1 req/s — used only as a
  fallback / sanity check, not the capture path.)

## Decisions (locked 2026-06-xx)

- **Resolution:** raw ticks (every FULL-mode packet), downsample later.
- **Storage:** date-partitioned **Parquet** on the data volume (+ existing
  GDrive backup); **nightly rollup to Postgres** for the analysis layer.
- **Scope:** NIFTY, wider chain — **ATM ±10 strikes** (21 strikes × CE/PE) for
  the **current + next weekly expiry**, plus **current + next-month futures**
  ≈ ~86 instruments. Well within KiteTicker limits.
- **Runner:** a **separate Railway worker** service from the same Docker image
  (`python scripts/options/capture_ticks.py`), independent of the web app.

## Architecture

```
morning (once)         scripts/options/select_instruments.py
                         kite.instruments("NFO") + NIFTY spot (ltp)
                         -> ATM±10 CE/PE (2 expiries) + 2 futs
                         -> data/options/tokens/<date>.json   (token list for the day)

market hours (worker)  scripts/options/capture_ticks.py
                         KiteTicker FULL mode on the day's tokens
                         on_ticks -> buffer -> flush to Parquet every N sec
                         -> data/options/ticks/date=<d>/nifty_<HHMMSS>.parquet

nightly (rollup)       scripts/options/rollup_ticks.py
                         raw Parquet -> 1-min bars per instrument
                         (OHLC, last OI, depth imbalance, spread) -> Postgres options_bars
```

**Tick schema (Parquet):** `recv_ts, exch_ts, instrument_token, tradingsymbol,
expiry, strike, opt_type, ltp, last_qty, volume, oi, oi_day_high, oi_day_low,
total_buy_qty, total_sell_qty, bid1..5 {price,qty,orders}, ask1..5
{price,qty,orders}`.

**Rollup table `options_bars` (Postgres):** `underlying, expiry, strike,
opt_type, minute, o/h/l/c, volume, oi, avg_spread, avg_depth_imbalance,
last_bid/ask`. Analysis queries hit this; raw Parquet (via DuckDB) for deep
microstructure dives.

## The one real gotcha — token sharing across Railway services

The daily Kite login writes `access_token.txt` to the **web** service's volume;
Railway volumes attach to a **single** service, so a separate worker can't read
that file. Options:
1. **Store the access token in Postgres** (a tiny `kite_session` row) that the
   daily login writes and the worker reads each morning. Both services already
   share the DB. **Recommended** — least infra, works across services.
2. Worker runs its own headless login (duplicate credentials/flow).
3. Push the token to the worker as an env/secret daily (manual-ish).

Go with (1): extend the login step to also upsert the token into Postgres; the
worker reads it on connect and on the daily ~08:00 refresh.

## Other implementation notes

- **Market hours + holidays:** reuse `market_service` (holiday calendar is on
  `main`) to run only 09:15–15:30 IST on trading days; idle otherwise.
- **Token expiry:** Kite tokens die daily (~morning); the worker reloads from
  the DB each trading morning and on auth errors.
- **Reconnect:** KiteTicker has built-in auto-reconnect; log gaps.
- **Retention:** keep raw Parquet N days locally, archive to GDrive; the
  rollup is the long-term queryable store.
- **Volume:** ~86 instruments FULL mode ≈ tens–hundreds of MB/day raw
  (compresses well). No scaling concern.

## Build order (small, reviewable steps)

1. `select_instruments.py` — NFO filter + ATM±N strike/expiry selection →
   token list. (Testable offline against a saved NFO dump.)
2. Token-in-Postgres: `kite_session` table + login writes it + a reader helper.
3. `capture_ticks.py` — KiteTicker FULL → Parquet writer (buffer/flush,
   market-hours guard, reconnect).
4. Railway worker service (same image, new start command) + env wiring.
5. `rollup_ticks.py` — nightly Parquet → `options_bars` + backup wiring.
6. (Later) analysis: join depth/OI features with order/fill events.

## Scope boundary

In scope: the capture + storage pipeline above (NIFTY). Out of scope for now:
BANKNIFTY/FINNIFTY (easy to add later), any trading/signals off this data, and
the depth-vs-orders analysis itself (that's the payoff, after we have data).
