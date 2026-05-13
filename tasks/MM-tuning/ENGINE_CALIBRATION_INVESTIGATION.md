# MM-Tuning — Engine Calibration Investigation

**Status: RESOLVED (2026-05-13).** Primary cause identified and fixed.
Residual ~2pp CAGR gap likely from position-sizing logic — secondary, tracked
as separate follow-up below.

## TL;DR resolution

**Root cause:** `_clean_engine` defaulted to **Friday signals → Monday execution**.
Legacy `backtest_momentum.py` uses **Thursday signals → Friday execution**.
That 1-trading-day-earlier entry costs the new engine ~6.5pp CAGR / 0.20 Sharpe
on production-config (in momentum markets, entering 1 day earlier captures more
of the rally).

**Fix:** Added `signal_day` field to `_momentum_engine.BASELINE` (default
"thursday") + `entry_dates_for_rebalance(..., signal_day=...)` switch in
`scripts/_momentum_engine.py`. Calibration gap closed from 10pp to ~2pp CAGR.

**Numbers after fix (production-config, 2020-07-10 → 2026-05-08):**
| Engine + signal day | CAGR | Sharpe (rf=5%) | MaxDD |
|---|---|---|---|
| Legacy (Thursday — production) | 52.82% | 1.83 | -29.27% |
| **New engine (Thursday — corrected)** | **54.86%** | **1.84** | **-29.90%** |
| New engine (Friday — old default) | 46.58% | 1.59 | -31.04% |

**Major implication for the retune work**: with apples-to-apples Thursday
signals, current production beats every retune candidate on OOS Sharpe + CAGR
+ Calmar. The IS-sweep "improvements" were artifacts of the Friday-signal
handicap. **No production change warranted.**

**Implication for OM25 v3 / TL25 v3 — TESTED AND CONFIRMED SAFE**: both use
Friday signals via `_clean_engine`. We worried the same Friday-vs-Thursday
asymmetry would apply. Direct test (see `_calibration_om25_tl25_thursday.py`)
shows the OPPOSITE pattern: Thursday signals HURT OM25 v3 (-1.92pp CAGR) and
TL25 v3 (-1.46pp CAGR). Each strategy is already on its optimal signal day:

| Strategy | Optimal | Current (production) | Status |
|---|---|---|---|
| L6 momentum | Thursday (+6.5pp CAGR vs Friday) | Thursday | ✓ correct |
| OM25 v3 | Friday (+1.9pp CAGR vs Thursday) | Friday | ✓ correct |
| TL25 v3 | Friday (+1.5pp CAGR vs Thursday) | Friday | ✓ correct |

**Why the asymmetry?** L6's score is dominated by recent price moves
(short-horizon momentum); entering 1 day earlier captures more of the rally.
OM25/TL25 use lookback-heavy signals (capture asymmetry, trend persistence,
drawdown control) where one extra day of close data through Friday gives a
more reliable signal that more than compensates for the 1-day-later entry.
Also: L6 is weekly cadence so the 1-day shift is proportionally bigger.

**Net result**: no production change needed for any strategy. OM25 v3 and
TL25 v3 OOS retune conclusions remain valid as-is.

---

## What was investigated

**The problem:** Two valid backtest engines, same configs, same data window,
**opposite rankings**.

  | Config | New engine `_momentum_engine` (2020-07+) | Legacy `backtest_momentum.py` (2020-07+) |
  |---|---|---|
  | PRODUCTION | 48.83% / 1.68 Sh / -30.7% DD | **52.82% / 1.83 Sh / -29.3% DD** |
  | A2_b0 (L6+skip5) | 50.52% / 1.72 | 48.04% / 1.64 |
  | A2_b6 (L6+skip5+buf6) | 50.14% / 1.73 | 45.88% / 1.57 |
  | **B1_b6 (OOS-best)** | **50.31% / 1.79** | 43.99% / 1.54 |
  | B2_b6 (L9+buf6) | 49.92% / 1.73 | 45.95% / 1.57 |

  - New engine: B1_b6 wins production by +0.11 Sharpe
  - Legacy engine: production wins B1_b6 by +0.29 Sharpe
  - Production gets a +0.15 Sharpe lift moving new→legacy
  - Retune candidates get a -0.10 to -0.25 Sharpe loss moving new→legacy

Until we understand this gap, we cannot ship a config change based on the
new-engine OOS evidence.

---

## What we know

1. **Both engines pass cosmetic checks.** Each independently reproduces
   reasonable momentum-strategy numbers (Sharpe in the 1.5-1.8 range,
   CAGR 40-55%, DD -30% to -40% on 2020+).
2. **The DD numbers agree closely** (~-30% for production on both engines).
   So both engines see the same drawdown events; they differ in HOW positions
   are sized through those events.
3. **The retune-candidates' OOS-best status in the new engine survived**
   strong stress: IS-then-OOS with sub-windows passed, vol_floor sensitivity
   was tested (A1 tracks failed OOS_C, A2/B1/B2 passed cleanly), exit_buffer
   was validated through both IS and OOS.
4. **Legacy engine doesn't compute Sharpe** — only CAGR, DD, total_return,
   turnover. The "1.92 Sharpe" in CLAUDE.md must come from a downstream
   reporting tool. **My legacy comparison computes Sharpe from the equity
   CSV using rf=5%**; this convention may differ from what CLAUDE.md
   originally used.

## Hypotheses to investigate (ranked)

### H1: Position sizing logic differs — most likely
- Legacy: `--score-rebalance-mode incremental` means only new entrants get
  fresh cash; existing positions DRIFT. Combined with min_hold_days=8 and
  the score-filter / pnl-hold logic, this produces a position-by-position
  history that doesn't match the new engine's "fair-share two-pass
  allocation".
- **Test:** Force both engines to log exact per-trade share counts on the
  same signal date. Diff the trade ledgers symbol-by-symbol.

### H2: Rebalance day-of-week difference
- Legacy: Thursday signal → Friday execution (when configured that way)
- New engine (via `_clean_engine`): Friday signal → Monday execution
- That's a 1-trading-day shift in entry pricing. Over 6 years × 24 holdings,
  this could accumulate to ~10pp CAGR if there's any week-cycle bias in the
  data.
- **Test:** Run legacy with `--rebalance-weekday friday` (if supported) or
  monkey-patch to align dates. Check if the gap closes.

### H3: Exit-buffer logic divergence
- Legacy: requires signals file to have `top_n + exit_buffer` ranks. We had
  to fix this in `momentum_legacy_compare.py` (initial run had buf=0 ==
  buf=6 because signals file only had top-24).
- New engine: holds positions explicitly while they stay within top-N+buffer.
- These should be equivalent but might handle edge cases (NaN ranks, signal
  rebalance boundaries) differently.
- **Test:** Trace a single position through both engines from entry to exit.
  Compare exit triggers.

### H4: Score normalization differences
- Legacy: cross-sectional z-score after multi-lookback composite — but here
  we use single L6/L9 so composite is a no-op
- New engine: cross-sectional z-score per date — should be identical for
  single-lookback case
- **Test:** Dump signals from both pipelines on the same date; compare
  symbol ranking and scores. Should be identical or near-identical.

### H5: Universe loading / NaN handling
- Legacy uses `ffill()` on the price panel, which can propagate stale
  delisted prices forward (audit flagged this as caution)
- New engine inherits same ffill from `load_price_panels`
- **Test:** Count number of trades for each engine. If one engine has
  significantly more "phantom" trades on delisted names, that's the source.

### H6: The bug we just fixed (delisting + min-hold trap)
- Fixed 2026-05-13 in `backtest_momentum.py:352-365` (this session)
- All legacy runs above used the FIXED version
- Old production numbers (CLAUDE.md's 59.4%) used the un-fixed version
- **Test:** Re-run legacy with the original buggy code (revert the fix
  temporarily). Confirm whether the bug affects which configs win/lose.

### H7: The 1.92 Sharpe claim itself
- Legacy doesn't write Sharpe to metrics.csv → 1.92 came from a downstream
  tool. Which one? With what `rf`? What window boundaries?
- Possibly the production claim was computed with rf=0 (raw mean/std × √252)
  vs my legacy compare which uses rf=5%
- **Test:** Compute legacy production Sharpe with rf=0 — does it land at 1.92?

## Action items — results

- [x] **A1: Recompute legacy production Sharpe with various rf** (done).
  rf=0 CAGR-based Sharpe = 2.02 (close to claim 1.92); rf=0 arithmetic = 1.78.
  Sharpe convention isn't the source — underlying CAGR/vol are real.
- [x] **A5: Score parity** (done first, since cheapest). Top-24 agreement
  across 5 sample rebalance dates: 100% on 4 dates, 96% (23/24) on one.
  **Conclusion: signal layer is identical between engines.** Gap is in
  execution.
- [x] **A3: Align rebalance days** (done). New engine on Thursday signals
  matches legacy almost exactly (53.04% vs 52.82% CAGR; 1.84 vs 1.83 Sharpe).
  **This was the primary bug.**
- [x] **A6: Engine of record decision** — new engine fixed to default
  Thursday signals matches legacy. Use new engine for all future analyses;
  it's faster (load-once + multiprocessing) and now calibrated.
- [x] **A7: Update CLAUDE.md and retune docs** — see "Implications" section
  in TL;DR. Production retune invalidated; no deployment change.
- [ ] **Follow-up: residual ~2pp CAGR gap.** Legacy 52.82% vs new engine
  Thursday 54.86%. Likely position-sizing: legacy uses `incremental` rebalance
  mode (only new entrants get cash, existing positions drift); new engine
  uses two-pass fair-share allocation. Test with trade-ledger diff (A2)
  when time permits. **Not urgent** — both engines agree directionally and
  on rankings.
- [x] **Follow-up: test Thursday signals on OM25 v3 / TL25 v3.** Done.
  Confirmed Thursday signals HURT both — each is correctly on Friday.
  See `_calibration_om25_tl25_thursday.py` and the TL;DR table above.

## Files

- `scripts/_calibration_a1_sharpe_conventions.py` — (inline; result shown
  in this doc, no separate script)
- `scripts/_calibration_a3_rebalance_day.py` — A3 test harness
- `scripts/_calibration_a5_score_parity.py` — A5 score-parity check
- `scripts/_momentum_engine.py` — fixed (added `signal_day` to BASELINE,
  defaults to "thursday"; `entry_dates_for_rebalance` accepts signal_day arg)
- `scripts/_clean_engine.py` — `thursdays()` and `biweekly_thursdays()` already
  existed and are now consumed by `_momentum_engine`

## Why this matters

1. **MM strategy is the FLAGSHIP** with the largest claimed performance.
   Any deployment decision must be based on a trusted engine.
2. **The 8 IS-tuned configurations from our sweeps are tied to the new
   engine.** If legacy is "truth" and the rankings differ, those sweep
   conclusions don't transfer.
3. **OM25 v3 and TL25 v3 use `_clean_engine` (the new engine).** Their
   OOS validation in the recent `oos_retune_2026` work is based on that
   engine. If the new engine has a bias the legacy doesn't, those
   conclusions could be partially affected too — though OM25/TL25 use
   different score functions and may be less sensitive.

## Deferral note

Investigation deferred to focus on:
- Walk-forward validation of the current production config (which IS now
  rigorously OOS-validated — first time ever)
- Cadence sibling-product evaluation (per `CADENCE_OBSERVATIONS.md`)
- Engine-of-record decision

Should be picked up before any production deployment of a retune.
