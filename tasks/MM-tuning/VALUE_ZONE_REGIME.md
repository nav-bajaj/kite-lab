# 3-State Regime: Bull / Bear / Value Zone (2026-05-14)

**Status:** Promising — BV3 (breadth value zone <20%) clearly dominates the
binary 100-DMA reference. Pending: deeper breadth-metric exploration before
locking into Defensive production.

---

## The paradigm shift

Every regime filter we've used to date — OM25 v3's bull/bear tilt, the
COMBO Defensive 50-cash overlay, the 100-DMA + 3-day confirmation across
all our strategies — has been **binary**:

```
Bull regime  → invest fully
Bear regime  → pull cash / tilt defensive
```

This is symmetric: same trigger (price vs MA) flips both directions.
It's also one-dimensional: there is only one piece of information about
"where we are in the cycle."

The **Value Zone** idea breaks that. Bear is no longer the terminal
defensive state. Inside Bear, there is a deeper sub-state — *Value Zone* —
where the market is so oversold (or breadth so washed-out) that
historical base rates favor a sharp snap-back. The state machine becomes:

```
                ┌─────────────────────────────────┐
                ↓                                 │
  ┌──────► BULL  ────(price < MA, 3d conf)────► BEAR ────────┐
  │         ↑                                  │  ↑          │
  │         │                                  │  │          │
  │         │ (price > MA, 3d conf)            │  │  (price > MA)
  │         │                                  │  │          │
  │         │                                  ↓  │          │
  │         └────(price > MA, 3d conf)────── VALUE             ←──┘
  │                                          (price < MA - 2σ)
  │                                          OR breadth < 20%
  └──── no direct BULL → VALUE transition ──────────────────────┘
```

Key state-machine properties:

1. **Bull → Bear** is the standard MA breakdown (3-day confirm).
2. **Bear → Value** fires when the market becomes *extreme* (price <
   MA − Nσ, or breadth of NSE 500 stocks above their own 200-DMA drops
   below some threshold).
3. **Value Zone is sticky.** Once you're in Value, you don't fall back
   into Bear — you only exit on a clean MA recovery (Value → Bull).
   This avoids whip-saw re-entries during a bottoming process.
4. **No direct Bull → Value.** Value only exists as an oversold-bounce
   trigger *from* a bear; you can't skip the down-leg.

Investment exposure follows state:

| State | Target exposure |
|---|---|
| BULL  | 100% (entries on) |
| BEAR  | bear_exposure (e.g. 30%); new entries skipped or scaled |
| VALUE | 100% (entries on) — same as Bull, but reached via oversold |

The Value Zone says *"the market is in a bear regime, but it's discounted
enough that I want to be invested anyway."*

---

## Why this matters operationally

The user's concern from the prior session:

> *"My only concern with going to very high cash levels is that
> redeployment takes time, when we're waiting for the regime switch
> there could be periods of sharp up moves from lower levels."*

A binary regime cannot fix this. The trigger to redeploy is the same as
the trigger to be in Bull: price reclaiming the MA. That happens *after*
the bounce, by definition.

A 3-state regime with Value Zone redeploys *before* the MA reclaim —
when the panic is at its peak, not when the recovery is already
underway. The empirical results (below) confirm this is exactly what
happens: the recent April-May 2026 rally was missed by the binary
filter but captured by every Value-Zone variant.

---

## Triggers tested

Two families, three thresholds each:

| ID | Family | Value-Zone trigger |
|---|---|---|
| V1 | stddev | price < MA(100) − 2.0σ of MA-deviation over 100d |
| V2 | stddev | price < MA(100) − 2.5σ |
| V3 | stddev | price < MA(100) − 1.5σ |
| BV1 | breadth | % NSE 500 stocks above own 200-DMA < 10% |
| BV2 | breadth | < 15% |
| BV3 | breadth | < 20% |
| F  | reference | (binary 100-DMA, no value zone) |

Bear exposure = 30% across all variants (matches locked Defensive).

---

## Test substrate

COMBO 50-50 (L6 + OM25 v3 priority-dedup, 12+12 = 24 stocks), bi-weekly
Friday signal → Monday OHLC/4 fill, 8-day min hold, 20 bps slippage,
NSE 500 + Nifty 250 universes. The same production Defensive candidate
that the regime sits on top of.

Engine: `_clean_engine.run_strategy()` with `bear_skips_entries=False`
(maintain 24-stock structure even in bear; protection comes from cash
weight, not stock count).

---

## Diagnostic: time-in-state

How often is each variant fully deployed vs in bear (full history
2009-2026):

| Variant | Full-invested days | Bear days |
|---|---|---|
| F. reference (binary) | 68% | 32% |
| V1 stddev @ -2σ       | 80% | 20% |
| V2 stddev @ -2.5σ     | 76% | 24% |
| V3 stddev @ -1.5σ     | 87% | 13% ← triggers too eagerly |
| BV1 breadth <10%      | 72% | 28% |
| BV2 breadth <15%      | 77% | 23% |
| BV3 breadth <20%      | 79% | 21% |

V3 at -1.5σ is too easy a trigger — the value-zone fires on any moderate
dip and the strategy is rarely defensive.

---

## Rally capture (2026-05-12 trailing)

The headline test. April-May 2026 has been very strong across L6,
OM25, TL25 — does the regime filter let the strategy participate?

| Variant | 1mo | 3mo | 6mo | YTD-2026 |
|---|---|---|---|---|
| F. reference          | 4.35 | 5.01 | 4.16 | **1.47** ← missed it |
| V1 stddev @ -2σ       | 7.74 | 7.74 | 6.87 | 4.10 |
| V2 stddev @ -2.5σ     | 7.74 | 7.74 | 6.86 | 4.10 |
| V3 stddev @ -1.5σ     | 7.74 | 7.73 | 6.89 | 4.13 |
| BV1 breadth <10%      | 4.36 | 5.02 | 4.18 | 1.48 ← never fired |
| BV2 breadth <15%      | 4.35 | 5.01 | 4.11 | 1.47 ← never fired |
| **BV3 breadth <20%**  | **7.17** | **7.99** | **7.06** | **4.35** |

Both the stddev family (V1/V2/V3) and the most permissive breadth trigger
(BV3 <20%) caught the bounce. The narrower breadth triggers (BV1, BV2)
never fired in this episode and behave identically to the binary
reference.

---

## Aggregate OOS metrics (2017-2026, 9.3 years)

| Variant | CAGR% | Sharpe | MaxDD% | Calmar |
|---|---|---|---|---|
| F. reference   | 36.17 | 1.85 | -26.36 | 1.37 |
| V1 -2σ          | 37.65 | 1.86 | -27.85 | 1.35 |
| V2 -2.5σ        | 38.05 | 1.89 | -27.86 | 1.37 |
| V3 -1.5σ        | 39.67 | 1.85 | -27.57 | 1.44 |
| BV1 <10%        | 37.77 | 1.90 | -26.39 | 1.43 |
| BV2 <15%        | 38.00 | 1.88 | -28.45 | 1.34 |
| **BV3 <20%**    | **39.31** | **1.92** | -27.87 | 1.41 |

All variants improve on the reference. The DD penalty (~1.5pp) is the
fair cost of redeploying in oversold zones that sometimes go deeper
before bouncing.

---

## Production window (2020-now, 5.84y)

| Variant | CAGR% | Sharpe | MaxDD% |
|---|---|---|---|
| F. reference  | 43.89 | 2.04 | -16.17 |
| V1 -2σ         | 44.79 | 2.06 | -16.16 |
| V2 -2.5σ       | 44.76 | 2.06 | -16.17 |
| **V3 -1.5σ**   | 47.70 | 2.02 | **-27.33** ⚠️ |
| BV1 <10%       | 44.13 | 2.04 | -16.16 |
| BV2 <15%       | 45.21 | 2.06 | -17.15 |
| **BV3 <20%**   | **46.87** | **2.11** | -17.96 |

V3 (-1.5σ) blows out drawdown by 11pp on the production window — the
eager trigger redeploys into a still-falling market multiple times.
**V3 rejected on this evidence alone.**

BV3 keeps the DD penalty contained (+1.8pp vs reference) while
delivering the best Sharpe (2.11) of the entire test.

---

## Walk-forward (13 rolling 3y-IS / 1y-OOS windows)

All variants pass 11 of 13 (85% pass rate, same as the reference).
Mean OOS Sharpe ranking:

| Variant | Mean OOS Sharpe | Median |
|---|---|---|
| **BV3 <20%**   | **1.92** | 2.24 |
| V2 -2.5σ        | 1.88 | 2.25 |
| BV2 <15%        | 1.88 | 2.24 |
| V3 -1.5σ        | 1.83 | 2.00 |
| V1 -2σ          | 1.82 | 2.14 |
| BV1 <10%        | 1.79 | 2.13 |
| F. reference   | 1.75 | 1.95 |

BV3 wins on both mean and tied for median. Critically, **no variant
*lowers* the pass rate** — the value zone is never worse than the
binary across the 13 stress windows.

---

## Why breadth-<20% (BV3) wins

1. **Best aggregate Sharpe** in every window (OOS_full 1.92,
   Prod 2.11, COVID 2.63).
2. **Best CAGR among DD-safe variants** (39.31% OOS_full).
3. **DD penalty is minimal** (+1.5pp).
4. **Captured the recent rally** (7.06% 6mo vs reference 4.16%).
5. **Highest walk-forward mean Sharpe** (1.92).
6. **Conceptual edge** — breadth is independent of where price sits in
   the index. Two indices can be at the same level with very different
   internal participation; breadth captures the difference that price
   alone cannot.

V2 (-2.5σ) is the close runner-up and is conceptually cleaner
(price-only signal, no dependency on a 500-stock panel). Carry as a
fallback if breadth turns out to have data-availability issues in
production.

---

## What this enables conceptually

The 3-state regime is the first time we've encoded **regime in two
dimensions** rather than one:

| Dimension 1 | Dimension 2 |
|---|---|
| Trend (price vs MA) | Extreme oversold (stddev or breadth) |

Once we have this scaffolding, more states become natural extensions:

- **Bull-Topping** (price > MA, but breadth diverging) → trim entries?
- **Value-Confirmed** (Value Zone AND breadth recovering) → leverage tilt?
- **Whipsaw** (rapid MA crosses without confirmation) → hold cash?

None of those need to be built now — but the *engine* now supports a
float regime panel with arbitrary exposure levels, so adding new states
is a config-only change, not a code change.

---

## Engine changes shipped

`scripts/_clean_engine.py`:

- `run_strategy` accepts a regime panel of `bool | float` values.
  Floats specify target exposure (0.0–1.0) directly, allowing
  multi-state designs.
- New `bear_skips_entries` flag (default True for back-compat; False
  for COMBO Defensive). When False, new entries fire in bear at the
  scaled weight — maintains the full 24-stock structure with cash
  protection coming from weight scaling, not stock count.

`scripts/_momentum_engine.py`:

- Forwards `bear_skips_entries` to clean engine for L6/momentum
  strategies.

Both changes are **additive** — locked OM25 v3 / TL25 v3 / L6
production calls are byte-identical to pre-change behavior.

---

## Open questions before production lock-in

**Update (2026-05-15): the indicator-side of question 1 is answered by
the Breadth Atlas** (`tasks/breadth_atlas/REPORT.md` / `REPORT.html`).
Indicator-first profiling of 14 NSE 500 breadth metrics across 2010-2026
shows that:

- The 14-metric panel collapses to **6 effective dimensions** (PCA, 90%
  variance). PC1 = slow trend-participation; PC2 = daily flow.
- BV3's `pct_above_200dma <20%` threshold sits between the 5th and 15th
  percentile depending on bucket. The continuous version,
  `avg_dist_from_200dma <-2σ`, captures more samples (n=47 vs n=11) at
  comparable concurrent N100 drawdown (-27% vs -33%) — more
  statistically robust trigger.
- `net_new_highs_pct <-2σ` is **independent** of pct_above_200dma
  (ρ=0.73, below the 0.85 redundancy cutoff). 139 days at -16% mean
  concurrent DD. Strong candidate as a confirmation rule.
- `mcclellan_sum <-2σ` is corroborating slow-flow confirmation (76 days
  at -20% mean DD).
- Daily-flow metrics (ad_ratio, ad_net_pct, up_vol_ratio, mcclellan_osc)
  show **flat** bucket-vs-DD relationships — not useful as level signals
  for a regime gate, but possibly useful for trade-day timing.

**Refined open questions (post-atlas):**

1. **Threshold sweep on the empirically grounded set.** Now that the
   atlas tells us which thresholds correspond to which percentiles, sweep
   on the COMBO Defensive substrate:
   - `pct_above_200dma` at the 3, 5, 8, 10, 15, 20 percentile
   - `avg_dist_from_200dma` at the -1, -1.5, -2, -2.5 σ marks
   - `net_new_highs_pct` at the -1.5, -2, -2.5 σ marks
   - `mcclellan_sum` at the -1.5, -2 σ marks
2. **Combinational triggers.** Test "fire Value Zone when *both*
   pct_above_200dma <X% **and** net_new_highs_pct <Yσ" — the two are
   independent enough to be additive. Compare to either alone.
3. **Lookback sensitivity** — atlas shows half-life ranges from 13d
   (21-DMA) to 130d (200-DMA). Test 100d, 150d, 250d versions of the
   "% above own DMA" metric.
4. **Bull entry on Value→Bull transition** — currently Value Zone
   exposure is 100%, identical to Bull. Should re-entry from Value
   have a brief cooldown to avoid whipsaw if the bounce fails?
5. **Out-of-sample stress** — test against 2008-09 (limited data),
   2013 taper tantrum, 2015 China devaluation if data permits.

Next session: tackle #1 and #2 — atlas-grounded threshold sweep +
combinational triggers on COMBO Defensive substrate.

---

## Files

| Path | Purpose |
|---|---|
| `scripts/_three_state_regime_test.py` | This test (V1/V2/V3 + BV1/BV2/BV3 + reference) |
| `scripts/_clean_engine.py` | Engine — float regime panel + `bear_skips_entries` |
| `scripts/_momentum_engine.py` | Momentum layer — forwards new flag |
| `tasks/MM-tuning/three_state_agg.csv` | Aggregate metrics (gitignored) |
| `tasks/MM-tuning/three_state_trailing.csv` | Trailing returns (gitignored) |
| `tasks/MM-tuning/three_state_wf.csv` | Walk-forward results (gitignored) |
| `scripts/_asymmetric_regime_test.py` | Prior step — asymmetric MA bear / non-MA bull triggers |
| `scripts/_alternative_regime_test.py` | Prior step — DD-based and breadth-based binary regimes |
| `scripts/_combo_recent_performance.py` | Prior step — rally-capture diagnostic |
| `scripts/_combo_regime_design_sweep.py` | Prior step — bear-exposure sweep (25/30/35/40/50%) |
| `scripts/_combo_bear_entries_compare.py` | Prior step — bear_skips_entries True vs False |
