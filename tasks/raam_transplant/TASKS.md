# raam_transplant — task breakdown

Owners: 🤖 agent, 👤 Navdeep. Every phase ends with a 👤 checkpoint —
results reviewed and direction confirmed before the next phase starts.

## Phase 0 — Diagnostics (no strategy changes)

| # | Task | Owner | Risk |
|---|---|---|---|
| 0.1 | ~~Data audit + refresh~~ **DONE** — panel through 2026-07-20; found + flagged the local NIFTY 100 regime-path split (repo `indices_data_historical` stale 05-08, insight-engine path fresh) | 🤖 | data-gap |
| 0.2 | ~~Reproduce L6 v2 baseline~~ **DONE** — `baseline_l6.py`; Sharpe 1.90 / MaxDD −29.4 reproduce docs tightly; CAGR 54.5 vs 59.4 = refreshed-panel drift (same engine code path, so data not logic). Turnover/hit are definitional — standardize via `summarise_metrics` in Phase 1 | 🤖 | lookahead |
| 0.3 | ~~Residual-correlation panel~~ **DONE** — `residuals.py` (reusable by-product); rolling L6-book crowding reconstructed 2017→now via `crowding_diagnostic.py` | 🤖 | compute-cost |
| 0.4 | ~~Diagnostic study~~ **DONE** — see G0 verdict below. Fixed a mis-specified breadth metric (top-40-rank breadth is tautologically ~1.0; switched to market-wide) | 🤖 | multiple-comparisons |
| 0.5 | 👤 checkpoint: **G0 verdict — crowding weak-green, breadth-throttle (E2) REFUTED** | 👤 | — |

### G0 verdict (2026-07-20, `runs/crowding_diag_*`)

- **Crowding → forward drawdown:** weak but directionally consistent. Spearman(crowding, fwd_maxdd_20) = **−0.19**; top crowding quintile −7.2% 20d DD vs −6.0% bottom. Forward *return* is flat across crowding buckets (Spearman ≈0) → **de-crowding may trim DD at ~no return cost.** Signal fades past 20d. **E1 proceeds, low prior on a large win.**
- **Breadth → forward outcomes:** **U-shaped, not monotone.** Low breadth (washed-out) = strong forward returns; mid-breadth = worst returns + deepest DD; high breadth = best. A linear breadth throttle (E2) would cut risk at the bullish lows — **refuted.** The only viable breadth signal is a non-linear mid-breadth regime flag, which duplicates the already-rejected `breadth_atlas/combo_3state`. **E2 dropped in its planned form.**
- **By-product:** the crowding gauge is shippable to the insight-engine admin panel regardless of E1's outcome.

## Phase 1 — E1: correlation-penalized selection (L6-DIV)

| # | Task | Owner | Risk |
|---|---|---|---|
| 1.1 | ~~Greedy corr-penalized scorer~~ **DONE** — `e1_l6div.py` (path-dependent greedy run inside score_fn; λ=0 reproduces L6) | 🤖 | lookahead |
| 1.2 | ~~Tune λ on IS, run OOS~~ **DONE** — λ*=1.0; net-of-slip CAGR +0.2/+3.3/+1.7pp OOS, Calmar 2/3 | 🤖 | overfit |
| 1.3 | ~~Gate + robustness~~ **DONE** — `e1_robustness.py`; smooth λ∈[0.5,1.5] plateau (not knife-edge), crowd-window 42/63/126 all positive | 🤖 | — |
| 1.4 | 👤 checkpoint: **E1 = robust qualified PASS** (locked λ=1.0). Turnover gate fails on artifact scale; cost_drag +0.3pp/yr absorbed in improved net CAGR | 👤 | — |

### E1 on OM25 Quality Momentum — transfers, but gentler

`om25_div.py`. Same greedy residual-correlation selection penalty on OM25's
capture-ratio score (z-scored so λ is on the E1 footing), production OM25
engine (Nifty 250, biweekly, top-25, exit-buffer 20, 20% stop). IS-tuned
λ*=0.5. OOS vs plain OM25: CAGR +1.0 / +1.9 / −2.3pp (OOS-A/B/C), Calmar
better 2/3, DD better in OOS-B. **Passes the E1 gate.** But the effect is
*smaller* than on L6 (λ 0.5 vs 1.0; overlap **96%** vs 90% — ~1 name swapped;
corr 0.999). Reason: OM25 is large-cap (Nifty 250, less theme-crowded than
L6's broad NSE 500) and its capture-ratio factor already leans away from
crowded high-beta names — so there's less crowding left to remove. OOS-C is
the soft spot (de-crowding hurt slightly in the recent large-cap era).

### E1 on OM25 in the NSE 500 universe — FAILS (the tell)

`om25_div_nse500.py`. Identical to `om25_div.py` except OM25 selects from
NSE 500 instead of Nifty 250. Hypothesis (broader/more-crowded universe →
nudge helps more) was **wrong** — it flips negative. IS: every λ>0 is worse
than λ=0. OOS vs plain OM25-on-NSE500: CAGR −3.7 / −1.8 / −0.2pp, Calmar
worse **0/3**, gate FAILS. (corr 0.998, overlap 91.5% — still a ~2-name tweak.)

**Why (the load-bearing insight):** the nudge's value depends on the *base
score*, not the universe. L6's score is pure momentum, whose top names crowd
into themes → de-crowding removes redundancy and helps. OM25's capture-ratio
score is a *quality* tilt that already selects structurally-diversified,
downside-protected names — it de-crowds implicitly. On the broader NSE 500,
that quality factor has even more room to express, so forcing extra
decorrelation *fights* it, trading CR-selected quality for worse diversifiers.
So: helps momentum-purity scores, redundant on quality-momentum (Nifty 250),
counterproductive on quality-momentum in a wide universe (NSE 500).

**E1 verdict:** robust, modest improvement — de-crowding L6's book by nudging out the 2-3 most residual-correlated names/week buys ~+1.7pp OOS CAGR and better Calmar in 2/3 windows, net of costs. Helps most in trending/crowding eras (2020-22, 2023-26), neutral-to-slightly-negative in low-momentum chop (2017-19). Not a production decision here — a validated candidate + the crowding gauge (Phase 3) are the deliverables.

## Phase 2 — E2: bottom-up breadth throttle

| # | Task | Owner | Risk |
|---|---|---|---|
| 2.1 | Implement breadth-throttle exposure panel (float regime_panel) | 🤖 | lookahead |
| 2.2 | Tune floor on IS only; rolling-window T1-style battery vs bare L6 | 🤖 | overfit |
| 2.3 | Judge against pre-registered E2 gate; calendar-year DD table | 🤖 | — |
| 2.4 | 👤 checkpoint: E2 verdict + direction | 👤 | — |

## Phase 2 — Paper pillars revisited (user-requested)

### E-LV: low-volatility as a conservative sleeve — VIABLE

`lv_revisit.py`. Reframed bar (not a momentum rival; judged vs NIFTY 100
buy-hold as the conservative alternative). Two paper-faithful choices:
EWMA(λ=0.94) vol (RiskMetrics), and low-vol paired with a trend gate
(close>200-DMA & positive 126d momentum) — the paper's warning that raw
low-vol overweights declining names.

FULL 2009-2026, net of 20bps, top-24 weekly:
| Strategy | CAGR | Vol | MaxDD | Sharpe | Calmar | corr→L6 | overlap→L6 |
|---|---|---|---|---|---|---|---|
| NIFTY100 buy-hold | 10.1 | 16.3 | −38.1 | 0.31 | 0.26 | — | — |
| LV_NAIVE | 12.7 | 12.0 | −31.7 | 0.64 | 0.40 | 0.67 | 1.7% |
| **LV_TREND** | **15.4** | **12.6** | −31.6 | **0.82** | 0.49 | 0.70 | 4.2% |
| L6 (momentum) | 37.9 | 23.6 | −37.7 | 1.40 | 1.00 | — | — |

Verdict: **LV_TREND beats the NIFTY 100 on return, vol, drawdown AND Sharpe**
with a near-disjoint book (~4% overlap) and ~half L6's vol — a real
different-character sleeve for a conservative investor. Paper's V+T pairing
confirmed (LV_TREND > LV_NAIVE every window). Caveat: lags in the recent
high-beta era (OOS-C CAGR 8.8%, ~index); DD stop is redundant (low-vol
already shallow). Better outcome than om25_alt's LV25 — the reframe + trend
pairing did it.

**Robustness (`lv_robustness.py`) — survives and IMPROVES under stress:**
- **Cadence/size:** edge strengthens with less churn — monthly/top-30 gives
  Sharpe 1.00 at ~2.4%/yr cost vs weekly/24's 0.82 at 4.8%/yr. Ideal for a
  conservative product (trades less, costs less, performs better).
- **Ingredients:** **realized-252d vol beats the paper's EWMA(0.94)** on every
  gate (realized+both: CAGR 16.5, DD −26.4, Sharpe 0.91 vs EWMA 15.4/−31.6/0.82)
  — another "simple beats the paper's instrument." Trend gate ("both") best either way.
- **Consistency:** beats NIFTY 100 on return in **69%** of rolling 1-yr windows and
  on drawdown in **70%**. Big downside protection in crashes (2011: −10% vs index −25%).
- **Honest limits:** lags in strong large-cap bull years (2021, 2025: −0.2% vs +9%);
  vs a true 60/40 (NIFTY100/10y gilt, 2017+) it wins on return+Sharpe (11.8/0.50 vs
  9.0/0.39) but its drawdown stays equity-sized (−32% vs 60/40's −24%). It's a
  **defensive-equity sleeve, not a bond substitute.**
- **Best production config:** realized-252 vol + trend gate + monthly + top-30.

### E-T: trend as a soft contributor to L6 — mechanic matters

`t_trend.py`. `final = L6_z + w * trend_signal`, grid w, read OOS.

- **Paper's breakout state (DONCH, 42d ±1): FAILS.** Hurts OOS mean CAGR at
  every weight (−1.8 to −3.4pp), worst in the strong-trend OOS-B (up to
  −12pp) — a "fresh-high-required" filter ejects consolidating winners,
  brutal in bulls. The paper's literal T mechanic does not transplant to
  stock momentum.
- **200-DMA-distance trend (our tooling), gentle w≈0.25: modest WIN.**
  OOS mean CAGR +1.97pp, **3/3 Calmar wins**, and it helps the choppy
  OOS-A window (+1.1pp) as hypothesised. Same gentle-dose-then-decay
  signature as E1 (w0.25 best, w0.5 less, w1.0 negative → real, not a spike).
  Caveat: 200-DMA distance partly overlaps momentum, so some of the gain is
  "more momentum." Robustness/stacking-with-E1 not yet run.

Synthesis across E1/E-LV/E-T: the paper's *directions* transplant; its
*literal mechanics* often don't — our own tooling (residual crowding, DMA
trend) beats the paper's GARCH-vol/ATR-breakout in Indian stock momentum.

## Phase 3C — De-crowding character morph

`de_crowd_character.py`. Push the E1 selection penalty from gentle to
aggressive (λ 0→40, pool 60→200), watch the character shift (FULL 2009-26):

| variant | λ | CAGR | Sharpe | DD | corr→L6 | overlap→L6 | book crowding |
|---|---|---|---|---|---|---|---|
| L6 | 0 | 37.9 | 1.40 | −37.7 | 1.00 | 100% | 0.080 |
| gentle (E1) | 1 | 38.4 | **1.43** | −38.0 | 0.99 | 91% | 0.073 |
| strong | 10 | 33.2 | 1.25 | −39.6 | 0.98 | 67% | 0.033 |
| aggressive | 20 | 28.5 | 1.10 | −41.1 | 0.95 | 51% | 0.005 |
| max+deep | 40 | 21.9 | 0.86 | −44.7 | **0.92** | **37%** | −0.018 |

**Findings:** (1) the mechanism works — it genuinely drops the book's internal
crowding (0.080 → ~0/negative) and overlap with L6 (100→37%). (2) **But you
can't decorrelate a momentum book by de-crowding it** — daily return corr to
L6 stays ~0.92 even at 37% overlap, because every name is still a momentum
stock riding the same factor. (3) The cost rises steeply — CAGR 38→22%,
Sharpe 1.43→0.86, and drawdown *worsens* (−38→−45%). You pay a lot for
"differently-named momentum" that still moves together.

**Verdict:** gentle E1 (λ=1) remains the only sweet spot — the sole setting
that beats L6. Aggressive de-crowding buys lower overlap and a genuinely
less-clustered book but never real decorrelation, at a heavy return/DD cost.
Genuinely different character comes only from *dropping momentum* (the E-LV
low-vol sleeve, corr 0.70 / overlap 4%), not from de-crowding momentum.

## Phase 3B — Crowding as a timing signal / proprietary indicator

`crowding_timing.py`. One crowding series (avg residual pairwise corr of the
top-50 momentum names), three angles.

- **Momentum Crowding Index (publishable):** clean daily series, range
  0.015–0.206, expanding-percentile context (lookahead-safe). Flags real
  episodes — all-time peak **early-2023 (Adani/Hindenburg, 0.206)**, then
  **2024-05 (PSU/defence, 0.173)**. Current 2026-07-20 = 0.115 (**89th pctile,
  elevated**).
- **Strategy lever — FAILS.** Throttling L6 exposure when crowding is
  extreme hurts at every threshold/floor (OOS mean CAGR −4.8 to −14pp,
  0–1 Calmar wins), worst in the OOS-B bull. High crowding coincides with
  strong momentum runs; cutting sits out the continuation. Do not retry.
- **What it means — the intuition FLIPS.** Forward L6 return by crowding
  quintile is **monotone increasing**: calmest quintile fwd-60d +3.2%/57% hit
  vs most-crowded +14.0%/78% hit. Crowded momentum historically KEPT working
  (higher forward return) — just with deeper interim shakeouts (the −0.19
  near-term-DD signal from Phase 0). It's a **trend-intensity gauge, not a
  sell signal.** Caveat: partly confounded with bull-regime (crowding is high
  in strong markets) — frame as observation, not a clean causal edge.

**Verdict:** not a lever; a viable **proprietary indicator** with a
counterintuitive, honest story ("momentum is crowded → historically kept
running, bumpier"). Productization = insight-engine module + validity-gated
framing + a subscriber-facing gauge. Founder decision pending.

**Generality check — lever on OM25 Quality Momentum (`om25_crowding_lever.py`):**
fails identically. Every threshold/floor loses OOS CAGR (best 90/70: −4.8pp
mean, worst 80/50: −14.7pp), worst in the OOS-B bull — same mechanism (high
crowding = mid-rally). Extra point: OM25 already has a 20% trailing DD stop,
so the lever's only supposed benefit is **redundant** — OOS-B drawdown is
unchanged (−32.8% with or without the lever, the stop already binds); it
only trims DD in OOS-C, and there at a proportional return cost (Sharpe
flat). Confirms: the crowding index is not an exposure-timing signal for any
momentum-family strategy.

## Phase 3 — E3: RC25 standalone — REFUTED (momentum in disguise)

`rc25.py`. Paper's full weighted-rank composite: M (126d vol-adj momentum) +
C (per-name avg residual correlation to pool, low=good) + T (200-DMA
distance), rank-summed, top-24, per-slot cash. IS-tuned weights 0.4/0.3/0.3.

OOS: RC25 ≈ L6 overall (FULL CAGR 37.0 vs 37.9, Sharpe 1.41 vs 1.40); helps
choppy OOS-A (DD −25.2 vs −28.8) and recent OOS-C, but gives up 11pp in the
strong bull OOS-B (55.3 vs 66.2) — C+T pull off the momentum leaders exactly
when leaders run hardest.

**Differentiation bar (om25_alt) — FAILS decisively:** daily corr to L6
**0.97** (bar <0.7), holdings overlap **66%** (bar <25%), Sharpe 1.41 (bar 1.5).
It is not a new product — it's a re-weighted L6 that trades bull-market
return for choppy-market smoothness at 97% correlation.

**Verdict:** closes the "is a 5th *momentum* portfolio warranted?" question —
**no.** The crowding/trend value is real but belongs as *tweaks to L6* (E1,
E-T), not a standalone composite. The genuinely different product is the
low-vol sleeve (E-LV), which is not a momentum book.

## Phase 4 — Close-out

| # | Task | Owner | Risk |
|---|---|---|---|
| 4.1 | RESULTS.md: decision, by-products, verification log | 🤖 | — |
| 4.2 | Failed branches → `docs/failed_experiments.md` | 🤖 | — |
| 4.3 | Optional: crowding-gauge productisation proposal for insight engine (TDD-scoped, separate approval) | 🤖 | scope-creep |
| 4.4 | 👤 checkpoint: merge/archive decision | 👤 | — |
