# Options Data Engine V1 — Consolidated Plan

> Supersedes the 2026-06-19 day-1 capture plan (see git history of this file).
> Consolidates that plan with the "MarketWorks Options Data Engine V1"
> technical handover document (2026-07). Analytics (gamma, vanna, IV
> surfaces, dealer positioning) are explicitly OUT of scope for V1 — this
> is the data platform every future options feature consumes.

## Objective

A worker that records, normalizes, and serves high-quality NIFTY options
market data in real time, becoming the single source of truth for: option
chain history, OI history, liquidity/bid-ask history, futures, spot index,
and historical chain snapshots. Every trading day of capture compounds into
a proprietary dataset the historical API cannot provide (depth history
essentially does not exist unless we record it).

## Corrections to the handover document

The handover PDF describes the stack as Supabase Postgres + Supabase auth.
That is not this codebase. Actual stack (verified):

- Database: **Railway Postgres**, shared by kite-api (SQLAlchemy + Alembic).
- Auth: **Clerk** (JWKS RS256, role in `publicMetadata.role`). The internal
  monitoring dashboard goes behind the existing `require_admin` dependency,
  not a new auth system.
- Frontend: Vercel (unchanged, consumes kite-api only — never Zerodha).

Everything else in the PDF (design philosophy, worker lifecycle, table set,
aggregation strategy, performance goals) is adopted below.

## Decision: same repo, new Railway service — NOT a new repo

The engine lives in **kite-lab**. Rationale:

- The repo already ships one Docker image (repo-root `Dockerfile`) that
  Railway builds; a second Railway service can reuse the **same image** with
  a different start command. This was the locked decision in the June plan
  and nothing in the handover changes it.
- The worker needs four things kite-lab already owns: the Kite login/token
  flow (`system_service`), the NSE holiday calendar (`market_service`), the
  Postgres models/Alembic migration chain, and `kiteconnect==5.0.1` (which
  bundles KiteTicker). A new repo duplicates all four plus CI, security
  scanning, and deploy config.
- The serving path is kite-api itself — chain snapshots and bars are read
  through existing FastAPI routes with existing auth. Splitting repos would
  put the schema owners on two sides of a migration boundary.

A new repo becomes worth it only if the worker later diverges in language,
team ownership, or image size. Not now.

Separation of responsibilities is preserved by process boundaries, not repo
boundaries: collector (worker service) != API (kite-api service) != UI
(Vercel). The worker exposes **no public endpoints** — only a localhost
health port for Railway's healthcheck.

## Code layout

```
kite-api/app/workers/options/
    __init__.py
    worker.py               # entrypoint + lifecycle state machine
    config.py               # env-driven settings (pydantic, like app.config)
    instrument_loader.py    # NFO master download + contract selection
    subscriptions.py        # token list management, mode assignment
    websocket.py            # KiteTicker wrapper: connect/reconnect/callbacks
    state.py                # in-memory chain state (the "current market")
    aggregator.py           # tick -> minute-bar builder
    persistence.py          # bulk inserts, snapshot upsert, Parquet writer
    scheduler.py            # IST market-hours gates (reuses market_service)
    health.py               # heartbeat row + local health endpoint
    models.py               # SQLAlchemy models (registered in app.models)
```

Run as `python -m app.workers.options.worker`. Business logic (state,
aggregator) stays import-pure and unit-testable offline against a saved NFO
dump + recorded tick fixtures; networking lives only in `websocket.py`.

Not in `scripts/` — the production scripts set is closed per repo
conventions, and this is a long-running service, not a pipeline step.

## Instrument universe (V1)

NIFTY only. BankNifty/FinNifty/stock options/far expiries deferred.

- NIFTY 50 spot index
- Current + next month futures
- **ATM ±10 strikes** (21 strikes × CE/PE) for the **current + next
  expiry** ≈ 86 instruments total

Decided 2026-07-27: ATM±10, not the full chain. Keeps tick volume, storage,
and bar counts small while covering the strikes where depth/OI actually
matter. Widening to the full chain later is a selection-config change only —
nothing downstream cares how many contracts exist. All instruments
subscribed in FULL mode (LTP, volume, OI, OHLC, 5-level depth).

**ATM anchor: spot, not futures** (decided 2026-07-27). NIFTY options
settle to the spot close, and for near expiries the forward-to-expiry is
within a few points of spot — whereas the monthly future carries ~20–60
points of basis to month-end, which would skew the window up by up to a
strike. Futures are captured anyway, so basis history (and later a
synthetic-forward "true ATM" from put-call parity) comes out of the
recorded data; it is not needed live.

**Intraday adjustment: widen, never re-center.** Initial window from spot
LTP at morning selection. If spot's nearest strike moves >= 2 strikes
(100 points) from the current window center, dynamically subscribe the
strikes newly inside ATM +/- 10 (KiteTicker supports mid-session
subscribe). Never unsubscribe intraday — dropping a strike punches holes
in its bar history, and even a wild trend day only grows the set to
~±14 strikes (~112 instruments). Next morning's selection re-centers.
Log window growth + max drift in daily_sessions.

Every contract gets a stable internal id — `NIFTY_20260730_25000_CE` —
because `instrument_token` is not durable across days. Tokens map to
contract ids at load time; everything downstream keys on contract id.

### Morning selection (daily, ~08:45 IST)

`kite.instruments("NFO")` filtered to `name == NIFTY` → identify current +
next expiry → upsert `instruments` rows (token, tradingsymbol, strike,
type, expiry, lot size, tick size, segment, exchange, contract_id) → write
the day's token list to the volume for crash recovery.

## Data flow

```
Zerodha KiteTicker (FULL mode, ~86 tokens)
   │  on_ticks
   ▼
state.py  — in-memory chain: {expiry → strike → {CE, PE}} + futs + spot
   │         updated per tick; never written per tick
   ├──────────────► every ≤10s: upsert option_chain_snapshots (latest only)
   │
   ├──────────────► aggregator: per-contract minute bars
   │                  └─ minute boundary → bulk insert option_minute_bars
   │
   └──────────────► raw ticks → buffer → Parquet flush every N sec
                      data/options/ticks/date=<d>/*.parquet  (Railway volume)

nightly              EOD flush + daily_sessions stats + compress + archive
```

Per-tick DB writes are forbidden (handover §14). Postgres sees one bulk
insert per minute (~86 rows) plus the snapshot upsert.

## Database (Alembic migrations in kite-api)

- `kite_session` — the daily access token. The existing login flow
  (system_service) additionally upserts the token here; the worker reads it
  at start and on auth failure. This solves the one real infra gotcha:
  Railway volumes attach to a single service, so the worker cannot read the
  web service's `access_token.txt`. Both services already share Postgres.
- `instruments` — contract metadata, keyed by contract_id, effective-dated.
- `option_minute_bars` — primary history. contract_id, minute (IST),
  o/h/l/c, volume delta, oi o/h/l/c, close bid/ask + quantities, avg
  spread, depth imbalance, quote count. Unique (contract_id, minute) —
  idempotent re-inserts, no duplicate rows.
- `option_chain_snapshots` — latest chain only, one row per contract,
  upserted; fast reads for the frontend/API. History lives in bars +
  Parquet, not here.
- `worker_health` — heartbeat, last tick ts, reconnect count, packets
  received, lag, memory, subscribed count, errors.
- `daily_sessions` — one row per trading day: duration, packet stats, gap
  count, data-quality flags.

Volume estimate: ~86 contracts × 375 minutes ≈ 32k bar rows/day (~670k
per month). Fine unpartitioned for a long time; partitioning is Phase 5.

Raw tick Parquet schema (per June plan): recv_ts, exch_ts, contract_id,
ltp, last_qty, volume, oi, oi day hi/lo, total buy/sell qty, bid1..5 and
ask1..5 (price, qty, orders). Retained N days on the volume, compressed
and archived (GDrive now, object storage later). At ~86 instruments this is
tens–hundreds of MB/day raw and compresses well — no scaling concern.

## Worker lifecycle (IST, via market_service holiday calendar)

- 08:30 instrument master download; 08:45 contract selection + DB upsert;
  09:00 token load + WebSocket connect + subscribe; 09:15–15:30 record.
- 15:30 stop subscriptions, flush aggregator + Parquet, write
  daily_sessions, compress logs. Process stays alive idle until the next
  session (Railway restart policy keeps it up).
- Non-trading days: idle loop, heartbeat only.

## Error recovery

Auto-recover, always, from: WebSocket drop (KiteTicker built-in reconnect,
target <5s, log the gap), Railway restart (re-read token list + kite_session
from durable storage, resubscribe, resume mid-session; the current minute's
partial bar is sacrificed and logged), Postgres unavailable (spool minute
bars to the volume, replay on reconnect — idempotent inserts make this
safe), token expiry (Kite tokens die ~daily; reload from kite_session on
auth error), unexpected exception (log, restart via Railway `on_failure`).

## Monitoring

- Worker writes `worker_health` continuously.
- kite-api gains admin-only read endpoints (behind `require_admin`, routed
  through the `security-reviewer` subagent before merge — NOT under
  `/api/system/*`): worker status, packets/sec, reconnects, latest tick
  age, missing contracts, session stats.
- A panel on the existing /admin dashboard (same pattern as the freshness
  panel). Never public.
- Alerting: freshness-monitor-style check — stale `worker_health.last_tick`
  during market hours raises a flag on /admin.

## Performance goals (adopted from handover §19)

No dropped packets; reconnect <5s; minute aggregation completes before the
next minute; no duplicate rows (unique keys, idempotent writes); chain
snapshot never staler than 10s during market hours.

## Local-first development (decided 2026-07-27)

Everything runs and proves itself locally before any Railway deploy:

- **Local stack:** worker runs on the laptop (`python -m
  app.workers.options.worker`) against local Postgres (existing
  `docker-compose.yml`), using the day's real access token from the local
  `access_token.txt` — no `kite_session` dependency needed for local runs
  (the reader helper falls back to the file when present).
- **Offline tests first:** instrument selection tested against a saved NFO
  master dump; aggregator and state tested against recorded tick fixtures
  (capture one session's raw ticks early, then replay them in tests). No
  network in unit tests.
- **Live local soak:** run the worker through at least 2–3 full market
  sessions locally. Exit criteria: complete bars for all ~86 contracts
  (375/contract/day), snapshot staleness <10s throughout, a forced
  Wi-Fi-drop reconnect recovered with the gap logged, and a mid-session
  kill + restart that resumes cleanly.
- **Only then Railway:** the second service, `kite_session` wiring, and the
  admin panel are the production step, not the development step.

## Phases

1. **Skeleton (local)** — worker skeleton (config, logging, lifecycle
   state machine, idle loop, local health endpoint); instrument loader +
   ATM±10 selection, offline-tested against a saved NFO dump.
   *Done when: selection produces the expected ~86 contracts from a fixture
   dump, and the worker idles/wakes on the market clock locally.*
2. **Market data (local)** — KiteTicker wrapper with reconnect; tick
   parser; live chain state; record a real session's raw ticks to Parquet
   and turn them into replay fixtures. *Done when: the chain updates in
   memory through a live session with every disconnect recovered.*
3. **Aggregation + persistence (local)** — minute builder, bulk inserts to
   local Postgres, snapshot upsert, daily_sessions, EOD flush; then the
   2–3 session soak from the section above. *Done when: soak exit criteria
   pass.*
4. **Production deploy** — `kite_session` migration + login upsert +
   reader fallback; second Railway service from the same image (start
   command override) + volume; env wiring. *Done when: the worker captures
   a full session on Railway unattended with parity vs a local run.*
5. **Monitoring** — admin endpoints + /admin panel, data-quality checks
   (gap detection, bar-count vs expected), staleness alerting.
6. **Optimization + retention** — table partitioning, Parquet
   compression/archival to GDrive/object storage, insert tuning, recovery
   hardening.

## Deployment notes

- Railway prod currently deploys from `beta_gtm_mvp`; the options-worker
  service can track its own branch — decide at Phase 1 whether it tracks
  `main` (cleaner) or the prod branch. The `kite_session` migration must
  land wherever the **web** service deploys from, since the login flow
  writes the token.
- One Kite API key supports 3 concurrent WebSocket connections; the worker
  uses one, the web app uses none (REST only). No conflict.
- New Railway service cost ≈ single-digit $/month + a small volume.

## Out of scope for V1

Greeks/IV/gamma analytics, BankNifty/FinNifty/stock options, far expiries,
client-facing UI, any trading signals off this data. Future workers (gamma,
vol surface, dealer positioning, flow) consume this engine's tables — they
never open their own Zerodha connections.

## Success criteria (handover §22, unchanged)

Worker runs through market hours unattended; every subscribed contract has
accurate 1-minute bars; chain snapshots continuously available; data
survives restarts and network failures; health monitoring clearly reports
status and quality; analytics can be added without touching ingestion; the
proprietary dataset compounds daily.
