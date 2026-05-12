# OOS Retune 2026 — Progress Log

Running notes from the retune work. The original plan + criteria are in `PLAN.md`;
this file captures what we've discovered, what we've decided, and what's still
open.

---

## Decisions locked in (OM25)

| Parameter | Locked value | Reason |
|---|---|---|
| Score weights (UC / CR) | **0.5 / 0.5** | User decision: 50/50 keeps product identity. CR-only is a separate "defensive" sibling for later. |
| Lookback | **252 days** | User decision: pinned at production default; suspicious of 189-day overfit despite +0.14 IS Sharpe. |
| Min observations | **220** | Consistent +0.10 Sharpe over 150. |
| Top-N | **25** | User decision: 30 is "too many stocks". |
| Exit buffer | **20** | Stage-2 sweep showed 20 ≥ 15. |
| Return filter | **ON** | +0.11 Sharpe at 50/50 weights. (At CR-only it didn't matter.) |
| ATR trailing stop | **OFF** | Confirmed from May 2026 review — adding any ATR stop costs 5-13pp CAGR. |

## Universe + cadence (provisional)

NSE 500 + biweekly looks like the front-runner *with* a regime filter. Without
the filter, NSE 500 fails the OOS Max DD criterion (-49% to -51% > -45%).

| Universe | Cadence | OOS CAGR | OOS Sharpe | OOS DD | Pass |
|---|---|---|---|---|---|
| NSE 500 | Monthly | 48.78% | 1.67 | -50.71% | ✗ DD |
| NSE 500 | Biweekly | 49.05% | 1.71 | -48.60% | ✗ DD |
| Nifty 250 | Monthly | 42.53% | 1.65 | -41.38% | ✓ |
| Nifty 250 | Biweekly | 42.42% | 1.65 | -40.77% | ✓ |
| Nifty 100 | Monthly | 32.06% | 1.38 | -41.90% | ✓ |
| Nifty 100 | Biweekly | 30.56% | 1.38 | -37.78% | ✓ |

---

## Regime filter exploration

**Goal:** reduce DD on NSE 500 to make it pass criteria, ideally without
giving back too much CAGR. Drawdown of ~40% (Nifty 250 baseline) was
flagged as "too much" by the user.

### Iteration 1 — 200 DMA, no confirmation, post-hoc
First test was post-hoc (apply regime mask to existing equity curve as
an upper-bound estimate). Showed dramatic improvements: NSE 500 biweekly
+ NIFTY 100 + 25% bear-exposure → 45.5% CAGR / 1.92 Sharpe / -25.8% DD.
Looked too good — suspected re-entry friction was missing.

### Iteration 2 — 200 DMA, no confirmation, in-engine
Modified `scripts/_clean_engine.run_strategy` to accept `regime_panel` and
`bear_exposure`. Ran the same sweep properly. Numbers were ~10pp lower
CAGR than post-hoc due to:
- Re-entry timing (must wait for next rebalance to re-enter)
- Slippage on regime-flip liquidations
- Cash drag during bear regime

Best in-engine pass: NSE 500 biweekly + NIFTY 50 + 0% bear → 40.4% CAGR /
1.80 Sharpe / -43% DD. Just barely under the -45% DD threshold.

### Iteration 3 — 100 DMA + 3-day confirmation hysteresis
User suggestion: faster MA + confirmation buffer to reduce false bear
signals. Big improvement.

| Config | OOS Sh | OOS CAGR | OOS DD |
|---|---|---|---|
| NSE 500 biweekly + NIFTY 200 + 25% | **2.07** | 37.7% | -25.8% |
| NSE 500 biweekly + NIFTY 100 + 25% | 2.03 | 36.9% | -23.1% |
| NSE 500 biweekly + NIFTY 50 + 0% | 1.94 | **40.3%** | -27.9% |
| Nifty 250 biweekly + NIFTY 50 + 25% | 1.77 | 27.1% | **-13.6%** |

vs same combo on 200 DMA: +0.1 to +0.34 Sharpe, 0-15pp better DD.

**Two clean candidates emerged:**
- **Candidate A — Best Sharpe:** NSE 500 biweekly + NIFTY 200 + 100DMA-3conf + 25% bear. 37.7% CAGR / 2.07 Sharpe / -25.8% DD.
- **Candidate B — Hits 40% target:** NSE 500 biweekly + NIFTY 50 + 100DMA-3conf + 0% bear. 40.3% CAGR / 1.94 Sharpe / -27.9% DD.

---

## Production report + allocation bug discovered (2026-05-10)

Generated comprehensive HTML report for the locked-in OM25 from
2016-01-01 → 2026-05-08 (10.4 years). Includes risk metrics (Beta,
Alpha, Information Ratio, Omega, Calmar, VaR/CVaR, Tail Ratio, Skew/
Kurtosis), per-index comparison (Nifty 50/100/250/500), drawdowns,
year-by-year, monthly heatmap, current holdings with PnL, last-10-day
PnL.

Final OM25 production-config metrics over 10.4 years:
- CAGR: 40.18%
- Sharpe: 1.70 (rf=5%)
- Max DD: -31.55%
- Total return: ~3,700%
- 25 holdings as of 2026-05-08, ~0% cash

Report file: `reports/om25_production_<ts>.html`

**Bug discovered during report review:** the `_clean_engine.run_strategy`
entrant-allocation loop is greedy/sequential — on rebalance days, each
new entrant is allocated `min(target_weight × pv, remaining_cash × 0.99)`.
When earlier entrants in iteration order consume cash, later entrants
get fractional allocations.

Example: CUMMINSIND on 2026-03-02 got 8 shares (notional ₹38k, weight
0.13%) instead of the ~4% target. 78 of 709 BUYs (11%) had < 50 shares.
Most are high-priced names where 1-share is plausible (HONAUT ₹28k,
PAGEIND ₹24k, 3MINDIA ₹20k), but some are mid-priced names like
CUMMINSIND that should have gotten ~10× more shares.

**Impact:** portfolio isn't truly equal-weight. Affected positions are
< 1% of portfolio and don't materially hurt CAGR. But the engine has a
real allocation flaw worth fixing for correctness.

**Fix plan (next):**
- Sell-first pass to compute total available cash
- Compute `per_entrant_cash = available_cash / num_entrants` (or use
  total target × num_entrants pro-rata)
- Allocate to each entrant up to that share, regardless of iteration order

## Engine fix applied (2026-05-10, same day)

Two-pass allocation in `_clean_engine.run_strategy`:
- Pass 1: each entrant gets `min(target, cash/n_entrants)` — order-independent
- Pass 2: redistributes leftover cash to entrants under target, with a
  10%-of-target threshold to skip dust trades

CUMMINSIND fix verified: 2026-03-02 entry now 204 shares (₹980k notional)
vs previous 8 shares (₹38k). BUYs <50 shares dropped 78 → 62 (most
remaining are legitimate high-price names like ABB/EICHERMOT). BUY count
1026 → 729 (dust trades eliminated).

Performance impact (locked-in OM25 from 2016-01-01):
- CAGR:    40.18% → 39.34% (-0.84pp)
- Sharpe:  1.70   → 1.66   (-0.04)
- Max DD:  -31.55% → -32.01% (-0.46pp)

Greedy allocation was giving implicit boost to earlier-ranked entrants
(better-scoring stocks); fixed version is genuinely equal-weight per
design. Honest numbers slightly worse than buggy numbers — correct trade.

---

## Stop-loss alternatives explored & rejected (2026-05-10)

Discovered prior "ATR" was actually 20-day return std (not real ATR).
Tested true ATR (OHLC-based) + Donchian channels, then a regime-aware
hybrid. All discipline-driven (IS-only first, then OOS).

**True ATR(14) × 6 — IS:** 29.05% / 1.60 / -25.5% (tied with fixed 20% on Sharpe)
**True ATR(14) × 6 — OOS:** 42.46% / 1.75 / -37.2% (loses on every metric vs fixed 20%)
- COVID 2020 was the failure mode: ATR widened in vol shock → looser stops just when needed tighter

**Donchian — IS:** best Sharpe 1.57 (20d). Doesn't beat fixed 20%.

**Hybrid: bull→ATR(14)×6, bear→fixed 20% — IS:** 26.74% / 1.51 / -26.1%
- WORSE than no-stop baseline (1.53)
- Reverse hybrid (sanity check) was BETTER (1.59) — failed in wrong direction
- Mechanism story didn't hold; switching stops at regime boundaries creates whipsaw friction
- Confirmed user's overfitting concern

**Net result:** locked-in stays as fixed 20% from peak. Multiple alternatives
tested rigorously; none survives IS+OOS validation. Sole exit mechanic
remains rank-at-rebalance + fixed 20% drawdown stop.

---

## Final addition: 20% drawdown stop (2026-05-10)

User flagged feeling insecure about a strategy with only rank exits and asked
to think of an alternative trailing stop other than 200 DMA (which we tested
and rejected). Solution: hard %-from-peak drawdown stop.

Engine trick: `atr_mult=0, atr_min_floor=X, use_trailing_stop=True` gives
a fixed X% drawdown stop without ATR scaling. Tested 15/20/25/30%:

| Stop | Exits | %Stop | OOS CAGR | OOS Sharpe | OOS DD |
|---|---|---|---|---|---|
| Baseline (no stop) | 830 | 0% | 44.78% | 1.83 | -36.57% |
| 15% | 1403 | 54% | 41.43% | 1.84 | -27.37% |
| **20%** | **1093** | **34%** | **43.57%** | **1.86** | **-31.44%** |
| 25% | 960 | 22% | 43.44% | 1.83 | -33.54% |
| 30% | 902 | 12% | 40.13% | 1.71 | -35.76% |

20% is the sweet spot: -1.2pp CAGR cost, +0.03 Sharpe gain, +5.1pp DD better.
Stop hit rate 50%, median PnL -0.2% — catches mean-reverters cleanly.
Locked in.

Final OM25 OOS-full performance: **43.57% CAGR / 1.86 Sharpe / -31.44% DD**.

---

## Engine bug fix + exit-mechanic verification (2026-05-10)

User flagged an exit-trigger question. Investigation revealed:

1. **Bug:** `_clean_engine.run_strategy` had both ATR trailing stop AND 200 DMA exit gated behind a single `use_trailing_stop` flag. With `use_trailing_stop=False` (our config), 200 DMA exit was NOT firing. All 830 exits in the locked-in winner were rank-based.

2. **Fix:** Split into two independent flags, `use_trailing_stop` and `use_dma_exit`.

3. **Empirical test:** With `use_dma_exit=True` enabled, the strategy made 1,408 exits (834 = 200 DMA, 574 = rank). 200 DMA exits had 39% hit rate / median -1.7% PnL. Net effect: -3.8pp CAGR / -0.07 Sharpe / +2.6pp DD reduction. Bad trade.

4. **Conclusion:** the locked-in `use_dma_exit=False` setting is the right choice — the strategy's biweekly rank-rotation + regime tilt provides sufficient exit discipline without 200 DMA over-pruning.

Sole exit mechanic in production:
- **Rank exit at biweekly rebalance** — when stock falls below rank 45 (top-25 + buffer-20)
- Stats: 830 exits over 17 years, 57.7% hit rate, +24.3% avg PnL, 172-day avg hold

---

## OM25 LOCKED IN (2026-05-10)

Final config: **Nifty 250 biweekly + NIFTY 100 100-DMA 3-conf regime + bull(50/50) → bear(0/100) tilt**.

Performance summary (OOS-full 2017-2026):
- 44.78% CAGR ✓ exceeds 40% target
- 1.83 Sharpe ✓ exceeds 1.5 target
- -36.6% Max DD ✓ below -45% threshold
- All sub-windows pass (Sharpe ≥ 1.5)
- ~24pp annualized alpha vs NIFTY 200 over 17 years

**Full writeup:** `RESULTS.md`

Key mechanism: regime tilts the UC/CR weight blend (not cash on/off). Strategy
stays 100% invested; bull regime uses production-identity 50/50, bear regime
rotates to defensive CR-only. Avoids cash drag and re-entry friction.

---

## Initial regime-as-weight-lever exploration (superseded by lock-in above)

User idea: instead of using the regime filter as a cash on/off switch,
use it to **tilt the score weight blend**:

- Bull regime → heavier upside-capture (more aggressive picks, e.g., 70/30 UC/CR)
- Bear regime → heavier capture-ratio (defensive picks, e.g., 30/70 UC/CR)

This is conceptually elegant because:
1. UC works well in bull regimes (high-momentum names lead)
2. CR works well in bear/transitional regimes (defensive selection)
3. The strategy stays **fully invested** — no cash drag
4. The "tilt" replaces the binary cash decision with a dynamic stock-selection bias

Implementation sketch:
- Closure-based score: `make_om25_regime_tilt_score(regime_panel, bull_weights, bear_weights)`
- On each signal date: lookup regime, apply weight blend
- run_strategy unchanged (no cash decisions); just smarter score function

To explore:
- Pairs to sweep: (bull_w, bear_w) ∈ { (70/30, 30/70), (60/40, 40/60), (70/30, 0/100), (60/40, 0/100) }
- Same regime signal: 100 DMA + 3-day confirmation, NIFTY 50 / 100 / 200
- Same universe candidates: NSE 500 biweekly, Nifty 250 biweekly

---

## TL25 retune (2026-05-11 → 2026-05-12)

### Setup
- Used the same `_clean_engine.run_strategy` engine + multi-window OOS framework as OM25.
- Created `scripts/tl25_v3.py` with `V2_LOCKED` defaults + parameterized `build_tl25_panels` and `make_tl25_score`.
- Baseline established with TL25 V2 spec: NSE 500, bi-weekly, equal-1/3 weights, 252/126/63 windows, top-25/buffer-20, 5x ATR-vol stop, 200 DMA exit ON. IS Sharpe ~1.55.

### IS-only sweeps (no OOS peeking)

1. **Stop variants** — Tested A1 (no stops), A2 (200 DMA only), A3 (20% DD only), A4 (V2 stack: 200 DMA + 5x ATR-vol).
   - **A3 won IS Sharpe (1.61, CAGR 30.57%, DD -28.21%).** V2's 200 DMA + 5x ATR-vol stack was worst.
   - Locked: 20% fixed DD stop, no 200 DMA exit, no ATR-vol stop.
2. **Weight variants (single config)** — Tested 11 weight combinations.
   - **A3 weights 40/20/40 (Offensive P+M) won Sharpe 1.61.**
   - Persistence-heavy 50/25/25 and 50/30/20 both at 1.60. DD-heavy variants under 1.55.
3. **Tilt variants (regime-aware)** — Tested bull/bear weight tilts with NIFTY 100 regime panel.
   - B2 (bear-DD-heavy tilt) had best IS Sharpe 1.62 but only 0.01 better than A3.
   - User decision: keep single config (A3) to maintain product diversity vs OM25 (which is regime-tilted).
4. **Windows / top-N sweep** — Tested persistence 126/252/378, momentum 21/63/126, drawdown 63/126/252, top-N 20/25/30, buffer 15/20/25.
   - V2 defaults (252/126/63 + top-25/buffer-20) remained optimal.
5. **Universe + cadence** — Tested NSE 500 / Nifty 250 / Nifty 100 × {weekly, biweekly, monthly}.
   - NSE 500 + biweekly won IS Sharpe by a hair (1.61 vs Nifty 250's 1.59).
   - Honored IS commitment, locked NSE 500.

### OOS validation (single-pass, no iterative tuning)

A3 baseline (NSE 500, biweekly, 40/20/40, 20% DD stop):
- **OOS-full Sharpe 1.52, CAGR 35.85%, DD -40.09%. PASS.**
- Sub-window Sharpes: 1.14 (2017-19) / 2.19 (2020-22) / 1.14 (2023-26) — all pass.

### Universe peek (deliberate; documented)
- Out of curiosity tested NSE 500 / Nifty 250 / Nifty 100 on OOS too.
- Nifty 250 actually won OOS Sharpe (1.55 vs NSE 500's 1.52).
- User: "sticking to NSE500 is better" — honored IS commitment over OOS-peeking.

### DD-reduction attempts (post-IS-OOS-validation)

User flagged DD concern (-40% on OOS). Tested two DD-reduction levers:

1. **45/35/20 weight tweak** — IS Sharpe 1.60 (-0.01), IS DD improved 2.70pp.
   - OOS test: **FAILED hard.** OOS-full Sharpe -0.07 vs A3, CAGR -4.23pp, **DD WORSE by 3.73pp**.
   - Classic IS-overfit catch. Rejected.
2. **Weekly rank-exit** — Initial IS test (2026-05-11) appeared to make things worse: Sharpe 1.55 (vs 1.61), DD -31.22% (worse), 0 `rank_weekly` exits despite my code edit using that label.
   - Investigated 2026-05-12: discovered engine bug. When `weekly_rank_check=True`, `signals` dict was populated for every Friday, and `entry_schedule` was built from `signals.keys()` — causing every Monday to be in `rebal_set` and skipping the dedicated weekly-rank-exit block.
   - **Fixed** `_clean_engine.py:236-246` to build `entry_schedule` only from `entry_signal_dates`.
   - Re-ran IS post-fix: **Sharpe 1.58 (-0.03), CAGR -1.30pp, DD +2.39pp BETTER**. Now a real DD-reduction lever.
   - OOS validation: **PASSED.** OOS-full Sharpe 1.53 (+0.01), CAGR 34.86% (-0.99pp), DD -39.00% (+1.09pp better). Unlike 45/35/20, robust across IS and all OOS sub-windows.
   - **Adopted as final TL25 v3 config.**

### TL25 v3 LOCKED IN (2026-05-12)

**Config:**
- Universe: NSE 500
- Cadence: bi-weekly entry + weekly rank-exit + weekly DD-stop checks
- Score weights: 0.40 × Persistence + 0.20 × Drawdown + 0.40 × Momentum
- Windows: 252 / 126 (squared) / 63
- Top-25, exit-buffer 20, max 7.5% per stock
- 20% DD stop from peak, no 200 DMA exit
- No regime tilt (single config — distinguishes from OM25 v3)

**Performance:**
- Full panel (2009-2026, 16.7y): CAGR 32.73%, Sharpe 1.40 (rf=5%), MaxDD -39.10%
- OOS-only (2017-2026, 9.3y): CAGR 34.86%, Sharpe 1.53 (rf=0), MaxDD -39.00%

**Saved as:** `scripts/tl25_v3.py:V3_LOCKED`
**HTML report:** `reports/tl25_v3_production_*.html`
**Full writeup:** `tasks/oos_retune_2026/RESULTS.md` — TL25 v3 section.

### Diversification check
Daily return correlation TL25 v3 (A3) vs OM25 v3 ~0.78; Jaccard holdings overlap ~0.22. Sufficient diversification. B2 tilt variant had higher correlation — confirmed user's intuition that single-config TL25 is the right complementary product.

### TL25 productionization
**STILL PENDING.** Same wiring needed as OM25 v3:
- Create `scripts/run_tl25_v3_portfolio.py` (mirror of OM25 v3 orchestrator)
- Add `tl25_v3` to `kite-api/app/config.py:UNIVERSES`
- Update `sync_service.get_latest_experiment_dir`
- Extend `positions_service` regex
- Add TL25 v3 step to `run_daily_pipeline.py`
- Update `tasks/trend_leaders/README.md` to feature v3 LOCKED at top

---

## Files

| Component | Path |
|---|---|
| Multi-window OOS evaluator | `scripts/multi_window_oos_eval.py` |
| OM25 stage-1+2 sweep harness | `tasks/om25/experiments/_om25_oos_retune.py` |
| OM25 50/50 stage-2 (locked weights) | `tasks/om25/experiments/_om25_50_50_stage2.py` |
| OM25 chosen-config × universes | `tasks/om25/experiments/_om25_chosen_universes.py` |
| OM25 OOS by universe | `tasks/om25/experiments/_om25_chosen_universes_oos.py` |
| OM25 regime post-hoc test | `tasks/om25/experiments/_om25_regime_filter_test.py` |
| OM25 regime in-engine (200 DMA) | `tasks/om25/experiments/_om25_regime_in_engine.py` |
| OM25 regime in-engine (100 DMA + 3conf) | `tasks/om25/experiments/_om25_regime_100dma_3conf.py` |
| GDF index backfill 2009-2019 | `scripts/backfill_gdf_indices.py` |
| GDF index extend to today | `scripts/extend_gdf_indices_to_today.py` |
| Index stitcher | `scripts/stitch_gdf_indices.py` |
| Engine modification | `scripts/_clean_engine.py` (regime_panel + bear_exposure) |
| Output runs | `experiments/oos_retune/` (gitignored) |
