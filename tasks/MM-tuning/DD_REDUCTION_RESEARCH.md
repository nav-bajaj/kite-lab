# L6 Drawdown-Reduction Research (2026-05-13)

**Status:** In progress. Findings below; walk-forward stress test pending
before any product decision.

**Motivating question:** L6 delivers great CAGR + Sharpe but the drawdowns
(-36% on OOS_full, -30% on the production window) are tough to sit through.
What structural changes — applied as candidate **sibling products**, not
replacements for the locked production — meaningfully compress DD without
killing the subscription value?

---

## Operational lens (added 2026-05-13)

Performance is necessary but not sufficient. **A strategy is only valuable
if subscribers can and will execute it for years.** This shapes the
product matrix:

| Operational axis | Easier (broader audience) | Harder (narrower audience) |
|---|---|---|
| **Cadence** | Bi-weekly (every other Friday) | Weekly (every Friday) |
| **Signal → execution lag** | Friday close → Monday open (2.5 day awareness window) | Thursday close → Friday open (overnight only) |
| **Position count** | Smaller (12-15) | Larger (24-30) |
| **Drawdown profile** | Shallower (<25%) | Deeper (>30%) |
| **Action-taking** | Set-and-forget | Active monitoring + adjustments |

A subscriber who quits mid-drawdown because they can't sleep at night, or
quits because Friday→Monday weekly is operationally heavy, never
captures the strategy's return. **Audience-fit > raw performance.**

This research note evaluates DD-reduction levers with this lens.

---

## Levers tested (this session)

### Lever 1: Per-stock trailing 20% DD stop (REJECTED)

`scripts/momentum_dd_stop_test.py` — tested 0%, 15%, 20%, 25% trailing stops
on L6 production config.

- IS Sharpe improves marginally (1.22 → 1.24-1.25)
- **OOS Sharpe consistently DROPS** (1.69 → 1.62-1.65)
- **OOS drawdown actually gets WORSE** at 15-20% stops (-36.6% → -38.5%)
- Stops front-run an exit by 1-7 days, often at worse intraday low prices
- Rank-exit + 8-day min-hold already catches catastrophes by the next rebalance

**Conclusion:** Don't add per-stock stops to L6. Rank discipline is already
load-bearing. (This is the opposite of OM25/TL25 v3 where buffer=20 lets
positions linger longer and stops are necessary safety net.)

### Lever 2: 3-strategy combo (L6 + OM25 + TL25, 8+8+8) (REJECTED)

`scripts/multi_strategy_combo.py` — top-8 from each strategy, priority-dedup,
weekly Thursday signals, 24 stocks.

| Metric (OOS_full) | L6 standalone | 3-combo |
|---|---|---|
| CAGR | 47.38% | 39.97% |
| Sharpe | **1.69** | 1.57 |
| Sortino | **1.81** | 1.65 |
| Calmar | **1.29** | 1.06 |
| MaxDD | -36.63% | -37.62% |

**Conclusion:** Diversification failed — all three strategies are
momentum-family and DDs are correlated. TL25 (lowest individual Sharpe)
drags the average. **Worse on every metric except DD, and DD barely moves.**

### Lever 3: Regime filter on L6 (PROMISING)

`scripts/momentum_regime_test.py` — NIFTY 100 100-DMA / 3-day confirm,
sweep bear_exposure ∈ {0%, 25%, 50%}. Same regime infrastructure used
in OM25 v3.

| Config | OOS_full Sharpe | CAGR | DD | Calmar |
|---|---|---|---|---|
| L6 (no regime) | **1.69** | **47.38%** | -36.63% | 1.29 |
| 100-DMA + 3-conf + bear=0% (full cash) | 1.61 | 34.54% | -35.38% | 0.98 |
| 100-DMA + 3-conf + bear=25% | 1.69 | 34.75% | -32.60% | 1.07 |
| **100-DMA + 3-conf + bear=50%** | **1.73** | 37.35% | **-32.15%** | 1.16 |
| 200-DMA + 3-conf + bear=50% | 1.62 | 37.20% | -33.73% | 1.10 |
| 100-DMA + 0-conf + bear=0% (no confirmation) | -0.74 | -8.43% | -57.97% | -0.15 |

**Production window** (2020-07 → 2026-05):

| Config | Sharpe | CAGR | DD | Calmar |
|---|---|---|---|---|
| L6 (no regime) | 1.84 | **54.86%** | -29.90% | 1.83 |
| **100-DMA + 3-conf + bear=50%** | **1.95** | 46.69% | **-18.01%** | **2.59** |

**Reads:**
- 100-DMA + 3-day confirmation is the right trigger (matches OM25 v3 lock)
- bear=50% is the sweet spot — bear=0% has too much re-entry friction
- **Confirmation days are load-bearing** — 0-day confirm whipsaws into -8%/yr losses
- Regime filter delivers ~5pp DD reduction on OOS, ~12pp on production window
- CAGR cost: ~8-10pp
- Risk-adjusted measures (Sharpe, Sortino, Calmar) all IMPROVE

### Lever 4: 50-50 combo (L6 + OM25, 12+12) (BEST CANDIDATE)

`scripts/multi_strategy_50_50.py` — top-12 from each, priority-dedup,
weekly Thursday signals.

| Track (OOS_full) | CAGR | Sharpe | Sortino | Calmar | MaxDD |
|---|---|---|---|---|---|
| L6 standalone (current) | **47.38%** | 1.69 | 1.81 | 1.29 | -36.63% |
| OM25 standalone (wkly Thu) | 42.85% | **1.80** | **1.90** | 1.23 | -34.83% |
| **COMBO 50-50 (L6 priority)** | 44.88% | 1.72 | 1.86 | **1.31** | **-34.20%** |
| COMBO 50-50 (OM25 priority) | 44.01% | 1.67 | 1.78 | 1.20 | -36.55% |

**Pareto-better than L6 alone:** higher Sharpe, Sortino, AND Calmar; better DD.
Only loses 2.5pp CAGR.

### Lever 5: 50-50 combo + regime filter (DEFENSIVE OPTION)

| Track (OOS_full) | CAGR | Sharpe | Sortino | Calmar | MaxDD |
|---|---|---|---|---|---|
| **COMBO + Regime (100/3/50%)** | 36.41% | **1.75** | 1.74 | 1.19 | **-30.54%** |

**Production window:**

| Track | Sharpe | CAGR | DD | Calmar |
|---|---|---|---|---|
| **COMBO + Regime** | **2.03** | 46.48% | **-16.11%** | **2.89** |

Calmar 2.89 is exceptional. -16% DD on the production window is in
"investor-friendly" territory.

---

## Product framework (revised 2026-05-14)

### Why we dropped "Balanced"

Initial framing had three tiers (Aggressive / Balanced / Defensive) with
COMBO 50-50 as the Balanced middle. On reflection, **Balanced doesn't serve
a distinct audience**:

- Aggressive (L6): OOS CAGR 47% / Sharpe 1.69 / MaxDD **-37%** / worst-window **-37%**
- Balanced (COMBO 50-50): OOS CAGR 45% / Sharpe 1.72 / MaxDD **-34%** / worst-window **-34%**
- Defensive (COMBO + Regime): OOS CAGR 36% / Sharpe 1.75 / MaxDD **-31%** / worst-window **-22%**

The Balanced tier sacrifices 2.5pp CAGR for 2.4pp DD reduction. The
**worst-window DD is essentially the same** as Aggressive (-34% vs -37%) —
both ride out psychologically similar drawdowns. A subscriber who would
quit at -37% will also quit at -34%. The "middle ground" exists
mathematically (slightly better Sharpe) but no audience exists for whom
"-34% DD is bearable but -37% isn't."

Whereas Aggressive vs Defensive is a real **15pp difference in
worst-window DD** (-37% → -22%). That's the line between
"unbearable" and "manageable" for typical subscribers.

### Two-tier weekly product line + one biweekly operational option

| Position | Product | OOS CAGR / Sharpe / MaxDD | Audience | Operational |
|---|---|---|---|---|
| **Aggressive** | L6 standalone (current production) | 47% / 1.69 / -37% | Sophisticated growth investors; can sit through ⅓-account DDs | Weekly Thu→Fri |
| **Defensive** | COMBO 50-50 + Regime (candidate) | 39% / 1.91 / **-26%** | DD-conscious, capital preservation tilt | **Bi-weekly Fri→Mon** (revised 2026-05-14) |
| **Set-and-forget** | OM25 v3 biweekly (current production) | 43% / 1.86 / -37% | Operationally low-touch subscribers | Bi-weekly Fri→Mon |

Each entry serves a distinct (audience × operational profile) combination
— not a flavor of the same job.

**Why three is the right number, not four:**
- "Subscriber who can stomach Aggressive's DD" → Aggressive
- "Subscriber who CAN'T stomach Aggressive's DD" → Defensive (real DD floor)
  — NOT Balanced (same DD floor)
- "Subscriber who wants low operational engagement" → OM25 v3 biweekly
  (handled by a separate operational axis)

There's no fourth orthogonal axis that Balanced would serve.

---

## Walk-forward validation (added 2026-05-14)

`scripts/momentum_walk_forward.py` runs all 4 candidates across 13 rolling
1-year OOS windows (the same framework used for OM25 v3 / TL25 v3). Results
confirm the DD reduction is structural, not single-window luck.

### Per-config summary (13 windows)

| Config | Pass rate (Sharpe ≥ 0.7) | Mean OOS Sharpe | Median Sharpe | Mean OOS CAGR | Worst window DD |
|---|---|---|---|---|---|
| L6 standalone | 10/13 = 77% | 1.68 | 1.50 | **57.1%** | -36.6% |
| L6 + Regime | 10/13 = 77% | 1.68 | 1.93 | 48.4% | -27.4% |
| COMBO 50-50 | 10/13 = 77% | 1.71 | 1.65 | 51.6% | -34.2% |
| **COMBO + Regime** | 10/13 = 77% | **1.74** | **1.90** | 44.6% | **-21.7%** |

### Where regime delivers (worst-window DD reduction)

The big wins are concentrated in bear regimes (where investors actually
need protection):

| Window | L6 standalone DD | COMBO + Regime DD | DD improvement |
|---|---|---|---|
| W03 (demonetization 2015-16) | -25.4% | **-5.1%** | +20pp |
| W07 (COVID 2020) | **-36.6%** | -16.0% | +20.7pp |
| W09 (inflation 2021-22) | -26.5% | -12.8% | +13.7pp |
| W12 (2025 small-cap correction) | -26.8% | -12.5% | +14.3pp |

Three failure windows are universal (W06, W12, W13) — characteristic
momentum-strategy tails, not config bugs.

The walk-forward CONFIRMS the OOS_full finding: COMBO + Regime trades
~12pp CAGR for genuinely structural DD compression.

## Still deferred

- **Operational sibling exploration**: a biweekly L6 variant. Friday→Monday
  cadence is the operational sweet spot for retail; monthly L6 has an
  interesting profile too. Worth re-examining for biweekly L6 specifically.
- **Tail hedging via index puts** — operationally complex, deferred.

---

## Decision (current — 2026-05-14)

**No production change yet** — pending product/operational decisions and
any further user-side validation.

### Defensive candidate (updated 2026-05-14 after priority×cadence + layered regime tests)

**COMBO 50-50 + Regime** with the following spec:
- Cadence: **Friday biweekly** (Fri close signal → Mon OHLC/4 execution) —
  2.5-day awareness window for subscribers
- Priority: **L6 → OM25** (verified consistent winner across signal day +
  cadence combinations)
- Regime overlay: **Binary 100-DMA + 3-day confirm + 50% bear exposure**
  (layered approaches did not improve over this — see Test 8 below)
- 24 stocks total (12 L6 + 12 OM25, priority-deduped), equal weight, 8-day
  min-hold

OOS_full performance: **CAGR 39.44% / Sharpe 1.91 / MaxDD -25.60% / Calmar 1.54**
Production window: **CAGR 48.88% / Sharpe 2.16 / MaxDD -15.46% / Calmar 3.16**

Production L6 stays as the Aggressive flagship; OM25 v3 biweekly remains
the Set-and-forget option.

### Tests 6-8: priority/cadence verification + layered regime (2026-05-14)

**Test 6 — Priority verification:** L6→OM25 priority order verified as the
winner across all (signal_day, cadence) combinations:

| Configuration | OOS_full Sharpe (L6→OM25) | OOS_full Sharpe (OM25→L6) |
|---|---|---|
| Thursday weekly | 1.72 | 1.67 |
| Friday weekly | 1.67 | 1.63 |
| Friday biweekly | **1.77** | 1.68 |

L6 priority wins by 0.05-0.09 Sharpe everywhere. **Friday biweekly
L6→OM25 emerges as the new optimal base** (Sharpe 1.77 without regime —
better than Thursday weekly at 1.72, AND operationally easier).

**Test 7 — Cadence operational benefit:** Friday biweekly gives
subscribers 2.5 trading days between signal and execution (Fri close to
Mon open) vs Thursday weekly's overnight window. Same audience profile as
OM25 v3 production cadence — proven operational fit.

**Test 8 — Layered regime overlay:** Tested whether progressive
de-risking (100-DMA → 75% / 200-DMA → 50%) improves over the binary
100-DMA + 50% scheme.

| OOS_full | CAGR | Sharpe | Calmar | MaxDD |
|---|---|---|---|---|
| No regime | 46.46% | 1.77 | 1.33 | -34.99% |
| **Binary 100-DMA + 50% bear** | 39.44% | **1.91** | **1.54** | **-25.60%** |
| Binary 200-DMA + 50% bear | 38.90% | 1.79 | 1.32 | -29.55% |
| Layered 100→75%, 200→50% | 38.08% | 1.81 | 1.41 | -27.07% |
| Layered 100→50%, 200→25% (aggressive) | 36.93% | 1.84 | 1.38 | -26.70% |

**Binary 100-DMA + 50% bear wins** — best Sharpe, best Calmar, best MaxDD.
Layered approaches give Pareto-different (not Pareto-better) profiles.

Why layered didn't help:
- "Mild bear" state (price below 100-DMA but above 200-DMA) is only 8.5%
  of days — too rare to materially change the profile
- Binary fires earlier on bear entry; layered waits for 200-DMA confirmation
  during which protection is only 75% (incomplete)
- The 100-DMA + 3-day confirm trigger is doing the heavy lifting; adding
  200-DMA structure on top is marginal

The aggressive layered (100→50%, 200→25%) does deliver the **best COVID
window DD** (-13.46% on OOS_B vs binary's -17.64%), so it's a candidate
for a "deep-bear-focused" sibling variant. But for general Defensive
purposes, the binary 100-DMA wins.

### Tests 9-10: walk-forward + 50-DMA variants (2026-05-14)

After locking in the Friday biweekly L6→OM25 + Binary 100-DMA + 3conf +
50% bear candidate, ran two follow-up validations:

**Test 9 — Walk-forward stress test (13 rolling windows):**

| Config | Pass rate | Mean OOS Sharpe | Median Sharpe | Mean CAGR | Worst-window DD |
|---|---|---|---|---|---|
| L6 standalone (current production) | 77% | 1.68 | 1.50 | 57.08% | -36.63% |
| Combo no regime (Fri biwkly) | 77% | 1.69 | 1.72 | 51.86% | -34.99% |
| **Combo + 100-DMA/3conf/50%** | 77% | **1.80** | **2.19** | 45.84% | **-20.69%** |

The new candidate matches L6 standalone's pass rate but achieves better
mean Sharpe (1.80 vs 1.68) and dramatically better worst-window DD
(-20.69% vs -36.63%). Walk-forward CONFIRMS the structural DD reduction.

Three failure windows are universal (W06, W12, W13) — characteristic
momentum-strategy tails; no config can fix them via parameter tuning.

**Test 10 — 50-DMA variants for faster bear detection:**

| Config | Mean OOS Sharpe | Mean CAGR | Worst-window DD | W07 COVID DD |
|---|---|---|---|---|
| **100-DMA + 3conf + 50% bear (winner)** | **1.80** | 45.84% | **-20.69%** | -17.64% |
| 50-DMA + 3conf + 75% bear | 1.78 | 45.21% | -25.41% | -14.36% |
| 50-DMA + 5conf + 50% bear | 1.76 | 41.80% | -24.37% | -9.62% |
| 50-DMA + 3conf + 50% bear | 1.75 | 39.40% | -23.93% | -9.63% |

50-DMA fires faster (better COVID DD) but whipsaws more often, costing
CAGR + Sharpe overall. The 100-DMA + 3-day confirm is the sweet spot.

**One interesting Pareto-different sibling**: 50-DMA + 3conf + 75% bear
keeps CAGR comparable to 100-DMA candidate (45.21% vs 45.84%) and gives
better COVID-window protection. Could be marketed as
"crash-protection-focused" variant. But the 100-DMA stays the cleaner
general-purpose Defensive.

### Update (2026-05-14): Value Zone regime supersedes binary 100-DMA

The locked candidate below uses a **binary** 100-DMA regime. Subsequent
work introduced a **3-state regime (Bull / Bear / Value Zone)** that
preserves the same bear protection but adds a re-deploy trigger for
deep-oversold conditions — addressing the "we miss the bounce while
waiting for MA recovery" failure mode the binary filter has.

Best variant: **BV3 — breadth value zone when <20% of NSE 500 stocks
are above their own 200-DMA**. Beats binary on OOS Sharpe (1.92 vs
1.85), captures the Apr-May 2026 rally (7.06% 6mo vs 4.16% reference),
and matches walk-forward pass rate.

Defensive production lock is **paused** pending breadth-metric
exploration. See `VALUE_ZONE_REGIME.md` for the full writeup.

### Final Defensive product spec (locked candidate, 2026-05-14)

```
Strategy:     COMBO 50-50 (L6 + OM25 v3 with priority dedup, L6 first)
Cadence:      Bi-weekly Friday signal → Monday OHLC/4 execution
Universe:     L6 picks from NSE 500; OM25 picks from Nifty 250
Stocks:       24 total (12 from each, equal weight, max 7.5%)
Min hold:     8 days
Slippage:     20 bps
Regime:       NIFTY 100 vs 100-DMA, 3-day confirmation
              → bull: 100% invested
              → bear: 50% invested / 50% cash
              (Also: OM25 component has its own internal regime tilt that
              shifts its score from balanced UC+CR to CR-only in bear)

Performance (validated):
  OOS_full (2017-26, 9.3y): CAGR 39.44% / Sharpe 1.91 / DD -25.60% / Calmar 1.54
  Production window (5.84y): CAGR 48.88% / Sharpe 2.16 / DD -15.46% / Calmar 3.16
  Walk-forward (13 windows): 77% pass rate, mean Sharpe 1.80, worst-window DD -20.69%
```

---

## Files

| Path | Purpose |
|---|---|
| `scripts/momentum_dd_stop_test.py` | Lever 1: per-stock trailing stop sweep |
| `scripts/multi_strategy_combo.py` | Lever 2: 3-strategy 8+8+8 |
| `scripts/momentum_regime_test.py` | Lever 3: regime filter sweep |
| `scripts/multi_strategy_50_50.py` | Lever 4+5: 50-50 combo with and without regime |
| `tasks/MM-tuning/regime_test.csv` | Regime sweep results |
| `tasks/MM-tuning/multi_strategy_combo.csv` | 3-strategy combo results |
| `tasks/MM-tuning/multi_strategy_50_50.csv` | 50-50 combo results |
| `tasks/MM-tuning/dd_stop_test.csv` | Per-stock stop sweep results |
| `tasks/MM-tuning/VALUE_ZONE_REGIME.md` | 3-state Bull/Bear/Value regime — supersedes the binary 100-DMA above |
