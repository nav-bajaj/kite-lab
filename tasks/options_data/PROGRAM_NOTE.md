# Options Program — Comprehensive Note

**Written:** 2026-07-30 · **Updated:** 2026-08-18 post-expiry · **Covers:** 2026-06-19 (first plan) → 2026-08-18 close
**Scope:** the options data engine (this folder), the Market Microstructure
Engine (`tasks/microstructure_engine/`), the research produced so far, and
the road to an autonomous options strategy.

---

## 1. What this program is

Marketworks is building a proprietary NIFTY options platform in three
deliberate layers, each depending only on the one beneath it:

    Zerodha ─→ Options Data Engine ─→ Microstructure Engine ─→ (future)
              capture, normalize,      IV, Greeks, gamma,        strategy +
              store, serve             regimes, positioning      execution

The founding premise (V1 handover doc, June): **own the data first**.
Depth/book history for Indian options effectively does not exist as a
purchasable dataset — the only way to have it is to record it, and every
trading day recorded is an asset nobody else has. Analytics were
deliberately out of scope for V1; they landed (Stage 1–2 of the
microstructure engine) only after the data layer was proven.

## 2. What exists today (all deployed, all validated)

### The capture worker (`kite-api/app/workers/options/`, Railway service)

A second Railway service from the same Docker image (`SERVICE_ROLE`
dispatch), fully autonomous on the market clock:

- **08:30** the web service's login mirrors the day's Kite token (paired
  with its api_key) into Postgres (`kite_session`) — the worker reads it
  from there; the two services share nothing else but the DB.
- **~08:31** selection: fresh NFO instrument dump → ATM ±10 strikes
  (100-pt window analysis strikes, 50-pt grid), current + next weekly
  expiry, both futures, spot ≈ 87 contracts. ATM anchors on **spot**
  (options settle to spot; near-expiry forward ≈ spot). Saved to the
  volume for crash recovery.
- **09:15–15:30** KiteTicker FULL-mode capture: every tick → in-memory
  chain state → (a) raw-tick Parquet on the volume (5-level depth,
  whole-book bid/ask totals — the fields no API sells), (b) minute bars
  bulk-inserted to Postgres, (c) 10-second chain snapshot upsert.
  **Widen-only intraday rule:** spot drifting ≥2 strikes subscribes the
  newly in-range strikes, never unsubscribes (no holes in history);
  next morning re-centers. Dead ticker self-heals with a re-read token.
- **15:30** EOD: flush, `daily_sessions` stats row, and (since Jul 29)
  auto-materialization of the day's IV/Greeks.
- **Monitoring:** 30s heartbeat → Postgres → admin-only API
  (`GET /api/options/worker-status`, R-026) → live card on /admin.
  1-minute stats lines in Railway logs as the second view.

### The bar dataset (`option_minute_bars`, Postgres)

One row per contract-minute: OHLC, per-minute traded volume, **OI
o/h/l/c**, end-of-bar best bid/ask, whole-book bid/ask totals,
tick-weighted **avg spread** and **avg depth imbalance**, tick count.
Three provenances (`source`): `hist` (30-day backfill, no depth), `replay`
(rebuilt from recorded ticks), `live` (built in real time). PK
(contract_id, minute) + conflict-ignore makes every path idempotent;
tickless minutes produce **no row** (gaps are information).

### The microstructure engine (`kite-api/app/microstructure/`)

Stage 1 complete (TDD, 19 spec tests red-first): per-minute **IV, delta,
gamma, vega, theta** for every option bar, in `option_greeks_minute` with
the assumption set and engine version on every row. The engine's first
self-correction is its best credential — see §4. Stage 2 readout
(gamma-by-strike, max-gamma strike, concentration) runs as research;
tables + /admin surface queued.

### Research & tooling (`research/` here + `tasks/microstructure_engine/`)

Backfill CLI (~30d minute+OI history), replay CLI (any recorded day →
bars, validated vs official candles), straddle simulator (real bid/ask
fills), TradingView-based visual explorers (candles + depth imbalance;
OTM depth comparison), analysis suites for both captured days.

## 3. How it was proven

- **Replay validation (the strong check):** day-one's 2.24M recorded
  ticks replayed through the aggregator reproduced Zerodha's official
  minute candles across 3,000 matched minutes — mean close error 0.0062
  pts, every official minute matched. Our bars additionally carry the
  depth columns official data doesn't have.
- **Live verification at every step:** wire test with real token (87/87
  contracts ticking, 0.09s staleness), post-close capture test, full
  dress rehearsal of the morning chain the night before day one
  (real headless login on the prod container → paired row → forced
  capture on the web-app credentials).
- **Two production sessions, zero intervention:** Jul 28 (expiry pin
  day; 2.24M ticks, 0 reconnects) and Jul 29 (gap + trend day; expiry
  rollover derived automatically, widen fired on the first spot tick,
  39,744 live bars, 0 DB errors).
- **Security:** two security-reviewer passes (APPROVE-WITH-NOTES both),
  risk-register rows R-025 (token in Postgres) and R-026 (heartbeat
  passthrough + the no-secrets-in-health_snapshot standing constraint),
  authz suite grown to 288 assertions.

## 4. What the data has said so far (honest ledger)

Sample: ~31 days of OHLC/OI bars, **16 days of depth**, 4 expiries,
ledger n=15 — everything below is diagnostic until the day-type library
grows. (Updated 2026-08-18; the daily OBSERVATIONS.md log in research/
is the running detail.)

**Added 2026-08-18 (the 08-18 cycle — the first TREND cycle):**

- **Ledger +141.3** (15 rows / 16 sessions, 11W +220.3 / 4L -79.0). The
  08-18 cycle added +62.2 over five sessions: +33.0, +13.7, -1.4, -2.8,
  +19.7. The 08-11 outage row stays empty by design.
- **Ledger verdict #2 — implied was CHEAP, 4/4.** EOD straddle vs the
  realized move to settlement on every day of the cycle: 1.00% vs
  -1.15%, 0.89% vs -0.99%, 0.74% vs -0.87%, 0.48% vs -0.55%. Program
  verdicts now 3 cycles implied-rich, 1 implied-cheap — and the cheap
  one was the trending cycle. **The short-vol edge is a range-regime
  edge, not a constant.**
- **Intraday-only, now measured across a whole cycle.** The same five
  sessions that made +62.2 intraday gave back -316.8 pts of index on a
  hold-through basis, and **-187.8 of that (59%) arrived in the five
  opening gaps** with the market shut. Strongest evidence yet for the
  standing constraint.
- **Down-diffuse tested for the first time (n=3)** and short premium
  was not punished (+33.0 / +13.7 / -1.4). The day-plan's up-drift
  rationale is now falsified on half its sample — a queued rewrite.
- **Record concentration did not pin.** Expiry 4 hit 47.6%
  concentration (an all-time high) with the wall at 24200, and spot
  settled 45 pts BELOW it at the day's low. Pin archetypes now read
  1 gravitational / 2 chased / 1 no-pin: concentration LEVEL alone is
  not a tradeable pin signal.
- **Thin credit was not the risk variable.** The thinnest credit on
  record (82.8, below the 93.0 that produced the worst day) paid +19.7.
  The separator was concentration's direction — decaying on 08-04,
  building on 08-18. Refines hypothesis 10.
- **Two measurement bugs surfaced**: IV percentile and the credit-
  thinness test are both DTE-blind (a 0-DTE credit compared against a
  4-DTE one), and so is the fixed 40-pt divergence flag band against a
  carry baseline that collapses -61.6 → -7.1 into expiry.
- **Threshold-calibration gate MET at n=15.** MAE cleanly separates the
  catastrophic losers from every winner but NOT the marginal ones —
  which is exactly the founder framework's argument for
  state-conditioned thresholds over price levels.
- **Ops: the post-EOD recycle fix held 5/5 unattended sessions**, 0 db
  errors, full contract coverage. The 08-11 incident is closed at n=5;
  push alerting remains the top ops gap.

**Added 2026-08-04 (the pivotal week):**

- **The short-vol distribution arrived in session six**: five straddle
  wins (+66.4 total) nearly erased by one expiry-day loss (-55.2, MAE
  -78.3 on a 93-pt credit). Net +11.2. Hypothesis 10 (thin-credit
  expiry risk) confirmed exactly as written.
- **Overnight carry measured**: Fri->Mon counterfactual -61.2 pts (gap
  + IV 8.4%->11.5% snap). Intraday-only until the ledger says
  otherwise.
- **Ledger verdict #1**: realized beat implied through the low-IV
  compression — the "cheap" premium was cheap.
- **Settlement mechanics under the new NSE timings (F&O to 15:40,
  standing)**: settlement = official close, established ~15:28-15:30;
  expiring options pin to intrinsic through the extended window.
  Greeks' 15:30 cutoff empirically confirmed.
- **Close-print structure**: the official close printed +150/+200 above
  the late continuous tape on both days of the new regime — a real
  recurring dislocation (chain converged to it on expiry day, stood
  apart on the non-expiry day). Divergence monitor is the top build.
- **Pin humbled**: expiry ≠ pin (1 of 2). Pin needs OI convergence,
  not a calendar slot.

**Confirmed / promising**

- **The expiry pin, measured three ways.** Jul-28: max pain nailed the
  close (3.7 pts); ATM OI tripled intraday while wings stayed flat; and
  in gamma terms, the max-gamma strike's share of total gamma climbed
  36% → 57% into the close, tracking the pin tick for tick. Total
  expiry-day gamma ran ~10x a normal day.
- **OI migration separates regimes.** Trend day: OI drained at overrun
  call strikes (→55–69% of morning base) and re-formed one rung above
  spot — the exact opposite of the pin signature. Regime classification
  (pin-gravity vs covering-fuel) is now a computable daily number.
- **Friction is two regimes.** Absolute spreads barely move all day;
  *relative* cost explodes only via premium decay into expiry closes
  (0.29% → 2.44% of premium). Books thin violently after ~15:20 on both
  days. Rule: time exits on expiry days; avoid the close everywhere.
- **The forward lives in the chain.** Put-call parity implies the
  forward to ±0.6 pts consistency across strikes. Adopting it
  (`b76-parityfwd-v1`) collapsed the same-strike CE/PE IV gap from +3.4
  vol pts to ~0.00 on all 23 days and raised IV coverage to 99.7%. The
  futures-de-carry alternative was **rejected empirically** (its own
  basis noise over-corrected to −1.8). ATM IVs sit 10–16% — India VIX
  territory — with expiry-day premium and post-gap crush both visible.
- **Depth imbalance is structural, not directional.** All OTM books sit
  bid-heavy (+0.5–0.8) on both sides; only deviations from a contract's
  own baseline can carry signal.

**Killed / parked (the discipline matters as much as the wins)**

- Day-one's ITM-put imbalance cluster (corr −0.35…−0.38 across five
  adjacent strikes) **did not replicate** on day two → parked pending
  regime conditioning.
- Naive ΔOI-vs-Δspot correlation ≈ 0 at 30-min granularity.
- PCR was coincident, not leading, in the backfill week.
- Short-straddle sim: both days profitable at 09:20 entry net of real
  spreads (+13.2 / +7.8 pts) — but the honest headline is that the
  regime that kills straddles (intraday runaway) **is not in the
  dataset yet**. No strategy conclusions until it is.

## 5. Incidents and what they hardened

| Incident | Fix now embedded |
|---|---|
| Token rejected in prod (`Incorrect api_key`) — local .env and Railway hold **different Kite apps** | `kite_session` stores (api_key, token) as a pair; every login writes both; worker uses them together |
| Postgres DiskFull mid-backfill (500MB legacy volume) | Volume grown to 5GB (with pre-resize pg_dump); bars ≈ 10MB/day |
| Part-file name collisions on replay | Sequence-suffixed Parquet filenames |
| UTC/IST bucket shift in analysis | All research queries tz-convert explicitly; bars store tz-aware minutes |
| SQLite/Postgres dialect drift in tests | Portable `date(minute)`, type normalization at the boundaries |

## 6. The road to an autonomous strategy (agreed direction, 2026-07-29)

Five layers; autonomy is earned per gate, never granted:

1. **Eyes** — ✅ done (this program).
2. **Brain** — ~70%: Stage 2/3 tables, daily auto-report, and a
   day-type library that needs 15–20+ sessions incl. an intraday
   runaway, a red gap, and a vol event. Accumulates automatically.
3. **Judgment** — a morning day-plan generator (regime forecast + IV
   percentile + walls → strategy, strikes, size, roll/stop rules) and
   an intraday reactive loop (OI-migration + live position Greeks).
   Exists today as research pieces, not yet a decision function.
4. **Hands** — order execution via Kite Connect. Deliberately unbuilt.
   Ships last, with position caps, daily-loss circuit breaker, admin
   kill switch, full decision audit trail, and a dedicated security
   review.
5. **Conscience** — founder-set risk config (max loss, vega/delta caps,
   size); paper-trading gate first (simulated fills against the *live
   recorded book* — we can model fills honestly because we record the
   depth), then one lot, then evidence-driven scale.

Rough shape: brain complete ~mid-August; paper trading through August's
expiry cycles; first supervised live lot early autumn **iff** the paper
evidence supports it.

## 7. Operating notes

- **Daily rhythm:** fully unattended. Optional glances: /admin ~09:20
  (green dot, CAPTURE, packets climbing) and the `eod:` log lines
  ~15:31 (recorder counters, bars inserted, greeks materialized).
- **Push freeze 09:00–15:40 IST** (F&O close moved to 15:40, NSE policy, standing) on `options_data_v1` (worker restart =
  ~1-min gap) and `beta_gtm_mvp` (web restart = SSE blip). Evenings are
  free; every deploy so far has been post-close.
- **Costs/limits:** 1 of 3 allowed WebSocket connections; REST usage
  negligible; positions SSE and the worker cannot collide (shared quote
  cache, separate paths). Worker volume ~230MB/day of raw ticks —
  **Phase 5 archival (gzip → GDrive → prune) is the one ticking clock,
  needed ~mid-August.**
- **Branch topology:** worker deploys from `options_data_v1`; web from
  `beta_gtm_mvp`; shared code (token store, heartbeat store, admin
  endpoint) cherry-picked between them. Convergence to `main` will
  close R-025/R-026's Alembic condition.

## 8. Status declaration & open items (updated 2026-07-30 EOD)

**V1 is COMPLETE per the handover doc's §22 success criteria** — all
seven met and verified across three unattended production sessions (see
TASKS.md for the itemized evidence). The program continues as
operations + the analytics/strategy track.

Done since this note was first written (same day): tick archival
(runway ~3 weeks → months), daily auto-report at EOD, error-lifecycle
fix (grace window + dot logic), founder risk-threshold framework
(research/NOTE_risk_thresholds.md — the MAE problem; probabilistic
state-conditioned calls, never price-predictive).

Remaining, ranked:

1. MAE ledger: paper-straddle section in the daily report + stored
   per-session rows (MAE, timing, underwater duration, regime at MAE).
2. Stage 2 gamma-profile table + /admin card (intraday regime read).
3. 08-04 expiry (Tue): straddle ledger's first verdict; second pin-day
   MAE path; gamma-concentration out-of-sample test. Arrives on its own.
4. Morning day-plan generator prototype (advisory; builds the call
   track record the autonomy gates need).
5. Stage 3 (dealer-sign assumptions — labeled ESTIMATED).
6. Threshold calibration at 15-20+ sessions (~mid-Aug).
7. Strategy engine + paper mode (per §6).
8. Housekeeping: GDrive offload of tick archives; merge to main
   (closes R-025/R-026 Alembic condition); old rebalance branch +
   redesign stash; delete the pre-resize dump.

## 9. On-track assessment (2026-07-30)

Deviations from the original plans, all deliberate and documented:

- **Local-first soak was compressed** (plan: 2-3 local sessions before
  Railway). Founder pulled prod forward for the 07-28 expiry-day test;
  compensated with the replay-vs-official-candles validation and a full
  pre-prod dress rehearsal of the morning chain. Outcome vindicated it
  (3 clean sessions), and the replay CLI now provides the equivalent of
  a soak for any recorded day.
- **Analytics arrived early** (V1 doc said out of scope). Sanctioned by
  the founder's Gamma Engine vision doc; built as a separate layered
  initiative (microstructure_engine) that consumes bars only — the V1
  ingestion pipeline was never touched, which is itself V1 criterion #6
  working.
- **Chain snapshot is a single JSON row** (handover suggested a table);
  chosen for atomicity + fast lookup, documented in bar_store.
- **No standalone `instruments` table** (handover §13): contract
  metadata rides on selection files (volume) + denormalized bar
  columns. Adequate for NIFTY-only V1; revisit when BankNifty lands.
- **Scope discipline held**: no BankNifty/FinNifty/stock options, no
  public APIs from the worker, no trading. The one scope addition
  (research/strategy studies) is the program's stated purpose and runs
  strictly on captured data.

Verdict: **on track, ahead of the original schedule, with scope
changes that were founder-directed rather than drift.** The main
watch-item is discipline going forward: strategy conclusions stay
embargoed until the day-type library reaches calibration size.

---

*Everything in this note is reproducible: raw ticks on the worker
volume are the authoritative archive; bars and Greeks rebuild from them
via the replay and materialize CLIs; every derived row carries its
engine version.*
