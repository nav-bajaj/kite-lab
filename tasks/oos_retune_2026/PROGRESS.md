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

## TL25 retune

Not yet started. Will follow OM25 pattern once OM25 winner is selected.

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
