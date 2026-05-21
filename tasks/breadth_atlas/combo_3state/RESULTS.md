# COMBO 3-state Breadth Regime — Results

**Status (2026-05-21): CLOSED. No production change.** The candidate
breadth-driven 3-state regime gate (D_BREADTH) was rigorously tested against
the current production NIFTY-100 close-vs-100dma 2-state gate (A_PROD).
After T1–T7, the verdict is that A_PROD's "5 positions / 81% cash" behavior
is the protection mechanism itself, not a bug — and any restructuring to
"24 stocks always" sacrifices materially deeper drawdowns and weaker
risk-adjusted performance in the live era.

See `PLAN.md` for the original test battery and pass/fail criteria.

---

## The opening question

The live dashboard for COMBO Defensive was showing only 5 holdings with
~81% cash. The user's first question: is this a bug? The diagnostic
(`combo_regime_diagnostic.py`) ran three variants over 2009-2026:

| | A_PROD (status quo) | B_BEAR_ENTRIES | C_ALWAYS_100 |
|---|---|---|---|
| `bear_skips_entries` | True (default) | False | False |
| `regime_panel` | NIFTY-100 bool | NIFTY-100 bool | None |
| `bear_exposure` | 0.5 | 0.5 | n/a |
| **End-state (May 2026)** | **8 holdings, 81% cash** | 24 holdings, 50% cash | 24 holdings, 0% cash |

A_PROD's behavior is **mechanical and deterministic**: during extended bear,
daily pro-rata sells drain share counts, biweekly rank-exits drop names
from top-24, and `bear_skips_entries=True` blocks all new entries. After 6+
weeks of bear, holdings dwindle to 5-10. The live "5 positions" is exactly
the design playing out — not a malfunction.

## C is dominated, dropped early

C_ALWAYS_100 (no portfolio-level regime gate, OM25 internal regime tilt
preserved) was dropped after the OOS-aggregate comparison:

| OOS-aggregate Sharpe | A_PROD | C_ALWAYS_100 | OM25 N250 alone |
|---|---|---|---|
| OOS-A | 1.27 | 1.64 | 1.19 |
| OOS-B | 2.71 | 2.30 | 2.12 |
| OOS-C | 1.61 | 1.42 | 1.75 |
| 2021+ | **1.99** | 1.63 | **1.77** |
| FULL | **1.55** | 1.47 | **1.58** |

OM25 *standalone* (production Nifty 250) on the same windows beats C on
2021+ Sharpe (1.77 vs 1.63) and FULL Sharpe (1.58 vs 1.47) with smaller
MaxDD. **Anyone who wants COMBO-style returns without the regime gate
would do better just deploying OM25 alone.** C was rejected for production
consideration before T1.

## Why does A_PROD have good CAGR despite ~14% of days in 81% cash?

Conditional return decomposition (over A_PROD's full equity history):

| Regime state | n_days | A_PROD daily return (annualised) | A_PROD vol (ann) |
|---|---|---|---|
| Bull (MA-regime True) | 2702 (67%) | **+55.2%** | 20.2% |
| Bear (MA-regime False) | 1347 (33%) | **+0.5%** | 8.4% |

Cumulative log-return decomposition: **99.8% of A_PROD's total return comes
from bull-regime days, 0.2% from bear-regime days.** A's "cash during bear"
isn't sacrificing growth — bear-regime days are essentially flat (+0.5%
annualised) once you average gains and losses. The protection (smaller vol,
smaller drawdowns during bears) improves path-dependence and compounding.

D_BREADTH by contrast earns ~12% annualised on those same bear-regime days
at 20.2% vol — that's where its higher CAGR comes from, AND where its
deeper drawdowns originate.

---

## The candidate — D_BREADTH

Replace A_PROD's NIFTY-100 2-state gate with a breadth-driven 3-state:

| Lever | A_PROD | D_BREADTH |
|---|---|---|
| Regime signal | NIFTY-100 close vs 100-DMA | breadth `avg_dist_from_200dma` |
| States | bull / bear | bull / bear / deep |
| Exposure (bull) | 100% | 100% |
| Exposure (bear) | 50% | 50% |
| Exposure (deep) | n/a | **100% (re-deploy at extreme oversold)** |
| State machine | binary with 3-day confirm | sticky-deep: `bull → bear → deep → bull` (no deep→bear) |
| Confirm days | 3 | 3 |
| Bear entries | skipped (`bear_skips_entries=True`) | **allowed at scaled weight** (`=False`) |
| End-state (May 2026) | 8 holdings / 81% cash | **24 holdings / 0.2% cash** |

The "sticky deep → bull only" semantics come from the principle that once
deployed at 100% during a panic, intermediate de-risking during recovery is
wealth-destroying. We only trim to 50% via a fresh bull → bear leg.

## The engine bug found mid-investigation

A preliminary D_BREADTH backtest ran with an unintended cash buffer —
when bear → deep triggered (target exposure 1.0), the engine stopped
selling but didn't actively top up existing holdings. Cash stayed parked,
gradually deploying only through biweekly rank-exit replacements.

**Fix (`scripts/_clean_engine.py`):** new opt-in parameter
`regime_redeploy_on_increase=False` (default off — production strategies
unaffected). When True and the target exposure increases vs the prior day,
the engine tops up existing holdings pro-rata to the new target weight.
Symmetric to the existing pro-rata-sell-on-decrease logic.

**Verification:** production OM25 v3 IS backtest produces byte-identical
results pre- and post-fix (CAGR 23.99% / Sharpe 1.03 / MaxDD -40.92% with
the flag's default False).

Post-fix D_BREADTH end-state: 24 holdings, 0.2% cash (the intended
behaviour). All numbers below are post-fix.

---

## Test battery results

### T1 — Walk-forward rolling 1-year Sharpe (the robustness gate)

Methodology: 3,865 rolling 1-year windows across 2010-2026. Compare D vs A
per window.

| | D wins Sharpe | D wins CAGR | D wins MaxDD | Median D-A Sharpe |
|---|---|---|---|---|
| Default D (after engine fix) | 58.9% | 65.6% | 26.4% | +0.047 |
| **IS-selected D** (T4 tuned) | **66.7%** | 70.5% | 25.1% | +0.196 |

Decision gate: ≥70% Sharpe wins for "deployable upgrade." **Both versions
fail. IS-selected D closer (66.7%) but still below the bar.**

Per-epoch (IS-selected D):
- 2010-2012: D wins 96.5% — dominant in V-bottom-rich era
- 2013-2015: 57.6% — coin-flip-plus
- 2016-2018: 69.3% — close to gate
- 2019-2021: 72.4% — passes gate (COVID-rebound era)
- 2022-2024: 49.3% — coin flip
- **2025+: 11.0%** — decisive A win; the live era

### T2 — Calendar-year breakdown (post-fix, default D)

D wins **10 of 18 years on Sharpe (56%)**, **6 of 18 on MaxDD (33%)**.

**D's best years** (V-bottom recoveries):

| Year | Sharpe spread | Context |
|---|---|---|
| 2012 | +1.34 | recovery from 2011 |
| 2017 | +1.29 | small-cap mania |
| 2013 | +1.06 | post-taper recovery |
| 2020 | +0.77 | COVID rebound (but MaxDD -28.8% vs A's -17.6%) |

**D's worst years** (slow grinding corrections):

| Year | Sharpe spread | Intra-year MaxDD spread |
|---|---|---|
| 2025 | -1.10 | D -21.6% vs A -7.4% (+14.2pp deeper) |
| 2022 | -0.57 | D -30.2% vs A -13.4% (+16.8pp deeper) |
| 2016 | -0.54 | D -20.7% vs A -12.0% (+8.6pp deeper) |

D's intra-year drawdowns are subscriber-unfriendly even when annual returns
look fine. -30% in 2022 is the kind of drawdown that triggers redemptions
regardless of subsequent recovery.

### T3 — Differentiation from existing portfolios

Daily-return correlation with L6 (NSE 500 momentum) and OM25:

| Window | A_PROD vs L6 | **D vs L6** | A_PROD vs OM25 N250 | **D vs OM25 N250** |
|---|---|---|---|---|
| IS | 0.82 | **0.92** | 0.80 | **0.89** |
| OOS-A | 0.86 | **0.92** | 0.76 | **0.84** |
| OOS-B | 0.84 | **0.91** | 0.86 | **0.90** |
| OOS-C | 0.82 | **0.92** | 0.85 | **0.93** |

PLAN gate: D's correlation with L6 should stay ≤ 0.85. **D fails by a wide
margin (0.91-0.92 in every window).** A_PROD passes (0.82-0.86).

The reason: A_PROD's cash buildup mechanism *decouples* its returns from
market-following strategies. D stays 100% deployed and tracks market
momentum more closely. **The 5-position cash buildup IS the differentiation
as well as the protection — they're not separable.**

A_PROD vs D_BREADTH directly: ~0.91 daily correlation. They're very similar
day-to-day; the differentiation between them comes from regime transitions,
not from daily behavior.

### T4 — Threshold sensitivity (IS-selected, then OOS-evaluated)

Nine threshold combinations swept for `avg_dist_from_200dma`, ranked by IS
Sharpe. Top-3 by IS all use `bear_entry=+0.05` (conservative bear); default
D thresholds rank **5th of 9** on IS. The pattern generalises:

| Thresholds | IS rank | IS Sharpe | OOS-A | OOS-B | OOS-C | 2021+ | FULL |
|---|---|---|---|---|---|---|---|
| **+0.05 / +0.10 / -0.10** | **1** | 1.356 | 1.549 | **2.672** | 1.502 | 1.887 | **1.658** |
| +0.05 / +0.10 / -0.15 | 2 | 1.317 | 1.634 | 2.439 | 1.568 | 1.803 | 1.629 |
| +0.05 / +0.10 / -0.05 | 3 | 1.255 | 1.468 | 2.513 | 1.472 | 1.781 | 1.569 |
| 0.00 / 0.05 / -0.10 (default) | 5 | 1.124 | 1.721 | 2.514 | 1.513 | 1.689 | 1.564 |

IS-selected D (conservative thresholds) vs A_PROD across windows:

| Window | A_PROD | IS-selected D | Δ |
|---|---|---|---|
| IS Sharpe | 1.15 | **1.36** | **+0.21** |
| OOS-A Sharpe | 1.27 | **1.55** | **+0.28** |
| OOS-B Sharpe | **2.71** | 2.67 | -0.04 |
| OOS-C Sharpe | **1.61** | 1.50 | -0.11 |
| 2021+ Sharpe | **1.99** | 1.89 | -0.10 |
| FULL Sharpe | 1.55 | **1.66** | **+0.11** |
| FULL MaxDD | **-25.6%** | -35.0% | -9.4pp |
| 2021+ MaxDD | **-15.5%** | -21.4% | -5.9pp |

D wins 3 of 6 Sharpe windows (IS, OOS-A, FULL) and loses 3 (OOS-B, OOS-C,
2021+) — narrowly. **Drawdown protection still strictly weaker everywhere
except IS.** Sensitivity tuning helps but doesn't fix the structural gap.

### T5 — Breadth metric sensitivity (IS-selected)

IS-winner: `net_new_highs_pct`. But it **loses OOS-A by 0.45 Sharpe** to
the IS-runner-up. The metric selection doesn't generalise cleanly — picking
on IS alone is risky. `avg_dist_from_200dma` is the most consistent metric
across windows despite ranking 4th on IS.

### T6 — Bear exposure sensitivity

| `bear_exposure` | IS Sharpe | OOS-A | OOS-B | OOS-C | 2021+ | FULL |
|---|---|---|---|---|---|---|
| **0.3** (IS winner) | 1.141 | 1.753 | 2.574 | 1.535 | 1.689 | 1.592 |
| 0.5 (default) | 1.124 | 1.721 | 2.514 | 1.513 | 1.689 | 1.564 |
| 0.7 | 1.103 | 1.673 | 2.436 | 1.480 | 1.676 | 1.526 |

T6 is clean — lower bear_exposure (0.3) wins on IS AND OOS. Modest edges
but consistent. Worth folding into a final D variant.

### T7 — Live snapshot (2026-05-08)

| | A_PROD | D_BREADTH (post-fix) |
|---|---|---|
| Final value (₹1M → ) | ₹99.5M | **₹191.6M** |
| Holdings count | **8** | **24** |
| Cash % | **81.0%** | **0.2%** |
| Sample symbols | BHARATFORG, FEDERALBNK, GVT&D, HINDCOPPER, NATIONALUM, POWERINDIA, SHRIRAMFIN, VEDL | Same 8 + 16 more (TITAN, MARICO, MUTHOOTFIN, AUBANK, KEI, ABBOTINDIA, ...) |

The 8 A_PROD stocks are a **subset** of D_BREADTH's 24 — A's protection is
the *absence* of holdings, not different holdings. D's final value is ~1.9×
A's (cumulative +5pp CAGR over 16 years), at the cost of ~5pp deeper FULL
MaxDD and worse recent-era drawdowns.

---

## Verdict — production stays as A_PROD

D_BREADTH **fails three of the four production-replacement gates**:

| Gate | D_BREADTH | Verdict |
|---|---|---|
| T1: Win Sharpe in ≥70% of rolling windows | 66.7% (IS-selected) | **FAIL** |
| T2: No year catastrophically worse than A | 2022 D-A spread -16.8pp DD, 2025 -14.2pp DD | **FAIL** |
| T3: Daily corr with L6 ≤ 0.85 | 0.91-0.92 every window | **FAIL** |
| T4: Edge holds across threshold variations | Pattern generalises | PASS |

Even with optimal threshold selection (T4 best), D loses recent-era
performance to A:
- Recent (2021+) Sharpe: A 1.99 vs D 1.89 — A still better
- Recent (2021+) MaxDD: A -15.5% vs D -21.4% — A meaningfully better
- 2025 calendar year: A +12% vs D -5% — A's defensive mechanism is winning *right now*

**A_PROD's "5 positions / 81% cash" behaviour IS the differentiation AND
the protection.** Removing it via D_BREADTH:
1. Loses the L6/OM25 decorrelation (D's daily corr with L6: 0.92 vs A's 0.82)
2. Loses the bear-day return suppression (D earns 12% annualised in bear; A earns 0.5%)
3. Loses the drawdown compression (D MaxDD consistently 5-15pp deeper)
4. Gains: a 24-stock structure that's more comprehensible to subscribers, ~5pp higher CAGR over the long term

The trade-off is real but the recent-era cost is too high to recommend the
swap. The 2022 (-30%) and 2025 (-21%) intra-year drawdowns would have
triggered subscriber concern that A_PROD avoided.

## Where the breadth regime *does* shine

D_BREADTH's edge is regime-specific and concentrated in **V-bottom
recovery years**:

- 2012: D +21.7pp return advantage over A (post-2011-bear recovery)
- 2017: D +26.9pp (small-cap mania)
- 2013: D +14.7pp (post-taper rally)
- 2020: D +46.6pp (COVID rebound)
- 2024: D +20.2pp (sustained rally)

Across rolling 1-year windows starting at 2020-03 (the COVID bottom), D's
Sharpe is 9.2 vs A's 6.0 — the breadth-driven full deployment during deep
captures the V-bottom recovery cleanly.

A_PROD wins specifically in **slow grinding corrections** where breadth
never crashes hard enough to trigger deep state. 2022 and 2025 are the
canonical examples.

This is a meaningful research finding even though D isn't a production
replacement. The two regime mechanisms protect against different failure
modes. **Neither is universally better.**

---

## Subscriber-clarity question

The original concern that started this investigation: COMBO live shows 5
stocks. Subscribers see a "Defensive Blend" portfolio that looks broken or
like a managed cash position. Two paths to address this:

1. **Strategy change** — D_BREADTH solves it but at the cost of materially
   worse recent-era drawdowns. Rejected for the reasons above.

2. **Product communication change** — frame COMBO as "tactical defensive
   equity that goes to cash during adverse regimes" rather than "always
   deployed 24-stock portfolio." Make the cash buildup a documented
   feature with clear narrative ("portfolio went defensive in bear regimes
   X, Y, Z and preserved capital while broad market lost N%"). Subscriber
   education, not strategy redesign.

The data points strongly to path 2 — subscriber clarity through framing
rather than mechanism change.

---

## What the work produced (useful by-products)

1. **Engine fix** (`scripts/_clean_engine.py`): new
   `regime_redeploy_on_increase` flag adds symmetric pro-rata-buy on
   target_exposure increase. Default off — production unchanged.
   Available for future regime-based experiments.

2. **State machine library** (`combo_breadth_3state.py`): sticky-deep
   3-state regime machine reusable for other portfolios' regime gates if
   we revisit.

3. **Confirmed structural insight**: A_PROD's cash-buildup-during-bear
   mechanism is the source of BOTH its differentiation and its
   drawdown protection. They are not separable. This affects how future
   COMBO-class portfolios should be designed.

4. **Validated breadth metric stability**: `avg_dist_from_200dma` is the
   most consistent breadth signal across windows (T5). Future regime work
   should default to it.

---

## File index

```
tasks/breadth_atlas/combo_3state/
  PLAN.md                       # original test battery + pass criteria
  RESULTS.md                    # this file
  combo_regime_diagnostic.py    # A vs B vs C (3-way regime variant test)
  combo_breadth_3state.py       # A vs B vs D_BREADTH (the candidate)
  walkforward.py                # T1
  yearly.py                     # T2
  diff_existing.py              # T3
  sensitivity.py                # T4 + T5 + T6
```

Engine change: `scripts/_clean_engine.py:run_strategy` — added
`regime_redeploy_on_increase` kwarg (default False, byte-identical for
production callers).

Run outputs (equity CSVs, transition logs, sensitivity matrices) are stored
under `runs/<ts>/` and gitignored (regenerable, ~50 MB).

## Reproducibility

```
# Initial 3-way diagnostic (A vs B vs C)
python tasks/breadth_atlas/combo_3state/combo_regime_diagnostic.py

# A vs B vs D_BREADTH (with engine fix)
python tasks/breadth_atlas/combo_3state/combo_breadth_3state.py

# Test battery
python tasks/breadth_atlas/combo_3state/walkforward.py
python tasks/breadth_atlas/combo_3state/yearly.py
python tasks/breadth_atlas/combo_3state/diff_existing.py
python tasks/breadth_atlas/combo_3state/sensitivity.py
```

End-to-end: ~30-40 min on a 2024 MacBook.

---

## Decision

**No production change. COMBO Defensive stays as A_PROD.**

The "5 positions / 81% cash" behaviour is the strategy's protection
mechanism, not a bug. Sensitivity-tuned D_BREADTH gets closer to A on
risk-adjusted performance but never matches its recent-era drawdown
protection. The breadth 3-state regime is a viable but regime-specific
alternative — strong in V-bottom recoveries, weak in slow grinding
corrections — and 2025-style corrections are the current era.

If we revisit COMBO in the future, the most productive angle from this
work would be a **hybrid** that combines D's deep-state re-deployment
intelligence with A's cash-accumulating defensive mechanism (e.g.,
breadth 3-state + `bear_skips_entries=True`). That's a different strategy
that should be tested in its own right, not a tweak to D.

For the immediate subscriber-clarity concern: pursue product communication
rather than strategy mechanism change.
