# Intraday / real-time layer — options, licensing posture, technical design

## 0. The gate first: market-data licensing

This was already flagged at insights_v2 close-out ("intraday/real-time
layer (needs data-licensing review)") and it is the one part of this
initiative that is **not** a pure engineering decision.

Facts as they stand:

- All our market data comes through a personal Zerodha Kite Connect
  subscription. Kite Connect terms are written for building apps for
  one's own trading; **publicly redistributing live exchange data to
  third-party viewers is exchange-licensed activity** (NSE real-time
  and even delayed-display feeds are governed by NSE data agreements,
  normally via authorized vendors).
- Our current public posture — EOD *derived analytics* (breadth
  percentages, ranks, scores computed from historical closes) — is
  materially different from re-displaying live quotes, and is the
  posture the earlier security/compliance passes reviewed.
- Displaying **derived aggregate indicators** intraday (e.g. "62% of
  NSE 500 above yesterday's 200-DMA right now", RRG coordinates) is a
  transformation, not a quote feed — a much better position than
  showing live per-stock LTPs — but it is still computed from
  real-time data, so it needs an explicit founder/legal decision, not
  an engineering assumption.

**Postures, in ascending risk/cost:**

| Posture | What users see intraday | Licensing exposure |
|---|---|---|
| A. EOD only (status quo) | yesterday-close analytics; "updates after market close" | none (reviewed) |
| B. Delayed derived indicators | aggregate indicators recomputed on a 15-min delayed basis, clearly labeled "delayed" | low, but confirm |
| C. Live derived indicators | aggregate indicators (breadth, RRG, list counts) refreshed every few minutes; **no per-stock live prices anywhere public** | needs review; defensible transformation argument |
| D. Live per-stock data | live prices/vol_ratio per stock in lists and stock pages | effectively requires an NSE data agreement; not recommended pre-revenue |

Recommendation: design for **C**, ship **B** first (same code path, a
lag parameter), and put the posture decision + rationale in the risk
register as a new row before anything intraday goes public. Per-stock
intraday values stay admin-only until/unless a proper data agreement
exists.

**DECIDED 2026-08-13 (founder): live route approved — build posture C.**
Register row still owed before public exposure; per-stock live quote
display remains excluded. See `DECISIONS.md` (includes the KiteTicker
single-connection streaming note: NSE 500 + indices ≈ 574 tokens, one
websocket connection holds 3,000 — multiple API keys unnecessary for
data volume).

## 1. What "live" should mean per module

Not everything should tick. Proposed refresh classes:

| Class | Modules | Cadence (market hours) |
|---|---|---|
| Live headline | Nifty level/day change, INDIA VIX, intraday breadth (% advancing, % above prior-day DMAs), stress nowcast | every 3-5 min |
| Live slow | RRG nowcast point (today's provisional tail point), sector RS today, list membership deltas ("3 new volume surges today") | every 15 min |
| EOD only | Everything historical: panels, ranks, scores, validity-badged lists, seasonality, analogs | 16:30 pipeline (unchanged) |

Two honesty rules, shown in the UI:

- Intraday points are **provisional** — Zerodha index values are
  preliminary intraday (the pipeline already re-fetches a 15-day tail
  for exactly this reason, `docs/zerodha_api_index_data_issue.md`).
  The intraday tail point on any chart renders in a distinct
  "provisional" style and is replaced by the EOD value after the
  pipeline runs.
- Intraday volume ratios must be **time-of-day adjusted** (raw
  vol/20d-avg is meaningless at 10:00). Needs an intraday cumulative
  volume curve — buildable from `nse500_data_hourly/` (already
  fetched) or a simple piecewise curve; a small research probe in this
  task folder should calibrate it.

## 2. Technical design (posture B/C)

The machinery is mostly in place:

- **Quotes**: `app/services/quotes_service.py` already wraps
  `KiteConnect.quote()` (batch; 500-instrument limit per call — NSE 500
  = one call) and `.ltp()` behind a TTL cache; used today for
  positions P&L. No websocket needed at these cadences — plain REST
  polling from the existing scheduler is simpler and sufficient.
  KiteTicker (websocket) only becomes worth it if we later want
  sub-minute updates.
- **Scheduler**: APScheduler already runs in kite-api
  (`app/scheduler/tasks.py`, IST-pinned). Add an `intraday_snapshot`
  job: cron mon-fri, every N minutes between 09:15-15:30 IST.
- **Compute**: a new `app/insights/intraday.py` engine (TDD):
  - inputs: latest quotes for NSE 500 + tracked indices; *yesterday's*
    DMAs/52w levels from the existing panels (no recompute);
  - outputs: `IntradaySnapshot` — timestamp, % advancing, % above
    prior 50/200-DMA, net new intraday 52w highs/lows, index changes,
    VIX, stress nowcast, RRG provisional coordinates, per-list
    intraday counts;
  - append each snapshot to a small on-disk day file
    (`cache/insights/intraday/<date>.jsonl`) so the day's intraday
    curve can be charted and survives a worker restart; the file is
    discarded after EOD consolidation (it is provisional data, not a
    historical record we redistribute).
- **API**: `GET /api/insights/intraday` returning the latest snapshot +
  today's curve, `Cache-Control: public, max-age=60`. Same
  unauthenticated read posture as siblings (R-023) — add the register
  note. If posture B: the job simply serves the snapshot computed
  ≥15 min ago (lag parameter), and the response carries
  `delayed_minutes`.
- **Frontend**: insights pages today are server components with
  `revalidate=900` and zero polling. Add one client hook
  (SWR, market-hours-aware like the existing positions hook
  `refreshInterval` pattern) that hydrates the headline strip and
  "live" pills; historical chart modules stay server-rendered. Reuse
  `flash-on-change` for tick transitions.
- **Freshness**: extend `freshness_service` with an intraday row
  (last snapshot age during market hours) so the admin panel catches a
  dead intraday job the same way it catches a frozen VIX file.

## 3. Ops constraints

- **Push freeze 09:00-15:30 IST** (standing rule: deploys restart live
  Railway services). An intraday job makes this rule more important —
  it also means the intraday layer must tolerate a mid-session restart
  (hence the on-disk day file, rebuild-on-start).
- Token lifecycle: Kite tokens die ~06:00 IST; `morning_login` (08:30)
  already handles refresh. The intraday job must degrade gracefully
  (skip + freshness alert) when the token is invalid, never crash the
  worker.
- Rate limits: one `quote()` call per cycle for stocks + one for
  indices is far inside Kite's 3 req/s historical/quote limits. Keep
  the cycle work in the scheduler thread pool, off the request path.

## 4. Open questions for the founder

1. Posture decision (A-D above) — gates everything else here.
2. Cadence: is 5 min for headline / 15 min for RRG acceptable, or is
   the ambition sub-minute (which changes the answer toward
   KiteTicker + more infra)?
3. Should intraday snapshots be admin-only at first (posture C
   mechanics, but flag-gated exposure) to de-risk the licensing
   question while we validate the UX?
