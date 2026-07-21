# raam_transplant — Results

**Status:** in-progress / paused for later continuation (NOT complete).
**Research phase documented:** 2026-07-21.
**Outcome so far:** 2 validated strategy candidates + 1 proprietary-indicator
candidate + 1 shipped engine; a cluster of clean negative results that
sharpen *where* the ideas do and don't work.

This task transplanted ideas from Giordano's *Ranked Asset Allocation Model*
(RAAM, 2018 Charles H. Dow Award) into the Indian stock-momentum line
(NSE 500, weekly), following the repo's diagnostic-first, pre-registered-gate
methodology. The single line to remember: **the paper's *ideas* transplant;
its *literal mechanics* usually don't** — our own simpler instruments beat
the paper's every time (residual crowding > its correlation math, DMA-distance
> its ATR breakout, realized vol > its EWMA/GARCH).

---

## At a glance

| # | Experiment | Question | Result | Probe |
|---|---|---|---|---|
| 0 | L6 baseline | Does the harness reproduce production L6? | ✅ Sharpe/DD match; CAGR drift = panel refresh | `baseline_l6.py` |
| 0 | Crowding diagnostic (G0) | Does book crowding predict forward DD? | Weak yes (−0.19), return-neutral | `crowding_diagnostic.py` |
| E1 | L6-DIV selection nudge | De-crowd *which* L6 names? | ✅ **Qualified pass**, robust (+1.7pp OOS, Calmar 2/3) | `e1_l6div.py`, `e1_robustness.py` |
| E2 | Breadth throttle | Cut exposure when breadth low? | ❌ Refuted (breadth is U-shaped) | in `crowding_diagnostic.py` |
| E-LV | Low-vol sleeve | A different-character conservative product? | ✅ **Viable**, improved under stress | `lv_revisit.py`, `lv_robustness.py` |
| E-T | Trend contributor | Add a trend term to L6? | ⚠️ Breakout state fails; gentle DMA modest | `t_trend.py` |
| — | Crowding gauge | A live per-book risk readout? | ✅ Engine shipped (TDD); UI pending | `kite-api/app/insights/crowding.py` |
| E3 | RC25 composite | A standalone 5th momentum book? | ❌ Refuted (0.97 corr to L6) | `rc25.py` |
| — | Crowding exposure lever | Time L6 / OM25 with the index? | ❌ Fails on both | `crowding_timing.py`, `om25_crowding_lever.py` |
| — | Momentum Crowding Index | A publishable market internal? | ✅ **Viable indicator** (counterintuitive story) | `crowding_timing.py`, charts |
| — | De-crowding character morph | Can we make a *different* momentum book? | ❌ No — corr stays ~0.92 even at 37% overlap | `de_crowd_character.py` |
| — | OM25-DIV (Nifty 250) | Nudge on Quality Momentum? | ⚠️ Transfers but gentler (+0.2pp) | `om25_div.py` |
| — | OM25-DIV (NSE 500) | Nudge on Quality Momentum, wide universe? | ❌ Fails — reveals it's score-, not universe-dependent | `om25_div_nse500.py` |

Windows throughout: IS 2009-09→2016-12; OOS-A 2017-19; OOS-B 2020-22;
OOS-C 2023→now; all net of 20bps slippage, next-day OHLC/4.

---

## Validated candidates (held for a productization decision — none deployed)

**1. Crowding-aware Core Momentum (E1 / L6-DIV).** Keep L6's momentum ranking,
but pick the top-24 greedily with a residual-correlation penalty (λ=1.0), so
the 2-3 most theme-crowded names each week are swapped for less-correlated
diversifiers. ~90% overlap with L6. Net-of-cost OOS CAGR +0.2/+3.3/+1.7pp,
Calmar better in 2/3 OOS, drawdown shallower in 3/4. Robust across λ∈[0.5,1.5]
and crowd-window 42/63/126. A modest, real upgrade — or an opt-in variant.

**2. Defensive low-vol equity sleeve (E-LV).** A genuinely different-character
product: ~half L6's volatility, ~4% holdings overlap, beats the NIFTY 100 on
return, vol, drawdown AND Sharpe (FULL: 15.4% / 0.82 Sharpe vs 10.1% / 0.31),
and beats the index on rolling-1yr return 69% / drawdown 70% of the time.
Best config: **realized-252 vol + trend gate (close>200-DMA & +momentum) +
monthly + top-30.** Honest limits: lags in large-cap bull years (2021, 2025);
its drawdown stays equity-sized, so it beats a 60/40 on return but not on DD —
a defensive-*equity* sleeve, not a bond substitute.

**3. Momentum Crowding Index (proprietary indicator).** A single daily series:
the average residual pairwise correlation of the top-50 momentum names — "how
much are the momentum leaders secretly one bet." Flags real episodes unprompted
(all-time peak Feb-2023 Adani/Hindenburg 0.206; May-2024 PSU/defence 0.173);
current ~0.115 (89th percentile). **Counterintuitive core finding:** high
crowding historically preceded *higher* momentum returns (fwd-60d +14%/78% hit
in the top quintile vs +3%/57% in the calmest), not reversals — it's a
**trend-intensity gauge, not a sell signal.** Confounded with the bull regime,
so it should be framed as an observation, not a forecast. Charts published
(`crowding_chart.html` full 16y, `crowding_2019.html` focused 2019+).

**4. Crowding gauge (engine shipped).** `kite-api/app/insights/crowding.py` —
TDD'd pure-function engine (7 spec tests) computing per-book residual crowding
+ a percentile. Not wired to any route/panel. Real-data check flagged that the
null-vs-random percentile saturates for momentum books; the useful metric is
the **own-history percentile** — the loader for that is the pending Step B.

---

## Negative results (documented; see `docs/failed_experiments.md` #6-11)

- **E2 breadth throttle** — breadth vs forward outcome is U-shaped; low breadth
  is contrarian-bullish, so a linear "cut when low" throttle de-risks at the
  best moments.
- **E-T ATR/Donchian breakout state** — a "must make fresh highs" filter ejects
  consolidating winners; brutal in bull markets.
- **EWMA/GARCH vol** — loses to plain realized-252 vol on the low-vol sleeve.
- **RC25 full composite** — 0.97 daily corr / 66% overlap with L6 = momentum in
  disguise; gives up 11pp in the OOS-B bull. Closes "is a 5th *momentum*
  portfolio warranted?" → no.
- **Crowding exposure lever** — fails on L6 *and* OM25; high crowding = mid-rally,
  so throttling exposure sits out the run. On OM25 it's doubly moot (its 20% DD
  stop already caps the tail).
- **OM25-DIV in NSE 500** — the de-crowding nudge flips negative; see insight #3.

---

## Key insights & takeaways (the durable output)

1. **Crowding is a *selection* signal, not a *timing* signal.** Using it to
   choose *what* to own (E1) works; using it to decide *whether* to be invested
   (exposure lever) fails on every momentum strategy tested. Owning a less-crowded
   version of the trend helps; trying to time the trend with crowding hurts.

2. **You cannot decorrelate a momentum book by de-crowding it.** Pushing the
   penalty to the extreme drops internal crowding to ~0 and L6 overlap to 37%,
   but daily return correlation to L6 stays **~0.92** — every name is still a
   momentum stock riding the same factor — while CAGR falls 38→22% and drawdown
   *worsens*. Genuinely different character comes only from *dropping momentum*
   (the low-vol sleeve: corr 0.70, overlap 4%).

3. **The nudge's value depends on the base score, not the universe.** It helps
   *pure-momentum* rankings (L6), whose top names crowd into themes. It's
   redundant on *quality-momentum* (OM25/Nifty 250, whose capture-ratio factor
   already de-crowds) and *counterproductive* on quality-momentum in a wide
   universe (OM25/NSE 500), where the penalty fights the quality factor. Deploy
   it on momentum-purity strategies only.

4. **High crowding ≠ danger; it's trend intensity.** Crowded momentum has
   historically kept working (higher forward returns), with deeper *interim*
   shakeouts. The naive "crowded = top" read is backwards — which is exactly
   what makes the index a *proprietary* (non-obvious) insight.

5. **The paper's ideas transplant; its mechanics don't.** Three independent
   confirmations: residual crowding beat its correlation ranking, DMA-distance
   beat its ATR breakout, realized vol beat its EWMA. Treat RAAM as an
   idea-generator, not a recipe.

6. **Low-vol only works once you change the question.** Judged as a momentum
   rival (om25_alt) it failed; judged as a conservative sleeve vs a buy-and-hold
   index it's a clear win — and lower churn (monthly) *improves* it. Framing was
   half the result.

---

## Reusable artifacts (by-products)

- `residuals.py` — beta-residual return panel (252d beta vs NIFTY 100, residual
  pairwise correlation). The workhorse behind E1, the gauge, and the index.
- `kite-api/app/insights/crowding.py` (+ `tests/test_insights_crowding.py`) —
  production-grade TDD'd crowding engine.
- `crowding_diagnostic.py` / `crowding_timing.py` — reusable forward-outcome and
  conditional-distribution harnesses.
- `chart_data.py` + `crowding_chart.html` / `crowding_2019.html` — the index
  visualizations (self-contained canvas artifacts).
- `explainer.html` — plain-English one-pager.

---

## Open threads — WHERE TO RESUME (task is intentionally not closed)

Ranked by my read of value. The founder wants to revisit for possible studies,
indicators, or portfolios.

**Highest value**
- **Productize the Momentum Crowding Index** as a subscriber indicator: an
  insight-engine module (daily series + own-history percentile + episode
  history), a validity study to lock the honest "trend-intensity, not a sell
  signal" framing, and a subscriber-facing gauge/chart. Bundle with the gauge
  (shares the residual engine). This is the most novel adjacent-value output.
- **Finish the crowding gauge (Step B):** swap primary metric to own-history
  percentile, build the loader that reconstructs L6's crowding history, expose
  one admin endpoint. Engine + tests already in kite-api.
- **Formalize E-LV as a strategy proposal:** run the monthly/realized/top-30
  config through the full OOS gate suite like a real portfolio candidate; if it
  clears, assign a stable universe ID + display name and decide product framing
  (defensive-equity sleeve). Consider fixing its recent-era lag with a light
  momentum/beta tilt inside the low-vol book.

**Worth exploring**
- **Stacking E1 + gentle DMA-trend (E-T) on L6** — never tested together; each is
  a small independent win.
- **Crowding on COMBO Defensive** — it blends L6 + OM25 and could *double up* on a
  theme both halves like; a natural place a crowding check might matter. Untested.
- **Sector/theme-cap as a cruder crowding control** — "max N per sector" may
  capture much of the residual-crowding benefit more transparently; compare.
- **Conditional market-internals content** — the index's forward-return
  distributions could seed more subscriber content (regime-conditioned reads).

**Lower priority / paper leftovers**
- Literal per-slot absolute-momentum cash circuit-breaker (low prior from the
  breadth U-shape).
- Multi-asset RAAM rotation (NIFTY / gold / gilts) — a separate task; data already
  fetched. Possible conservative rotation sleeve.

**Data hygiene (independent of this task)**
- Local strategy regime path `indices_data_historical/NIFTY_100.csv` was stale
  (2026-05-08) vs the insight-engine path (`Documents/indices_data_full`, fresh).
  Railway unaffected. The worktree symlink was repointed to the fresh dir for
  this research; the underlying repo file split should be reconciled.

---

## Commit log (chronological)

```
56b2c1a open task — PLAN with pre-registered gates, phased TASKS
8ebdd99 Phase 0.2 — reproduce L6 v2 baseline harness
5416dea Phase 0.3/0.4 — crowding diagnostic, G0 verdict
d47898e Phase 1 — E1 L6-DIV crowding-penalised selection
491cb2e Phase 1 — E1 robustness confirms qualified pass
81694a1 crowding engine (TDD) — book_crowding + null percentile
5647352 plain-English progress explainer (one-page HTML)
ee6fea9 E-LV — low-vol as a conservative sleeve (VIABLE)
de10078 E-T — trend as soft contributor to L6
ae9dac0 E-LV robustness — survives and improves under stress
d9de506 write-up — RESULTS.md, failed-experiments ledger, meta (interim)
0bbf2cb E3 RC25 — REFUTED (momentum in disguise)
10c2f50 crowding as timing signal / indicator
801cd06 de-crowding character morph + chart data export
472ff2c Momentum Crowding Index chart (published artifact)
790930a focused crowding-vs-NIFTY100 chart (2019+, dual axis)
86138b7 crowding exposure lever on OM25 Quality Momentum — fails too
fea4fda E1 selection nudge on OM25 Quality Momentum — transfers, gentler
95f95f7 E1 nudge on OM25-in-NSE500 — fails (score, not universe)
(+ this write-up commit)
```

Detailed per-experiment numbers live in `TASKS.md`; negative-result write-ups
in `docs/failed_experiments.md` #6-11. Run outputs are under `runs/` (gitignored,
regenerable from the probes).
