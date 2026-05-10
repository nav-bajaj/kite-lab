# OOS Retune 2026 — Implementation Checklist

Track this list as work progresses. Mark `[x]` when complete.
See `PROGRESS.md` for running findings; `PLAN.md` for original plan + criteria.

## 1. Multi-window OOS evaluation utility — DONE

- [x] Create `scripts/multi_window_oos_eval.py`
- [x] Smoke test against existing equity curves; baseline configs PASS

## 2. OM25 retune harness — DONE

- [x] Create `tasks/om25/experiments/_om25_oos_retune.py` (stage-1 + stage-2 sweep)
- [x] Stage 1 ran (~20 configs); CR-only won by Sharpe
- [x] Stage 2 ran (~36 configs around top-3); 189-lookback peak
- [x] **User decision**: keep 50/50 (CR-only as separate defensive sibling); pin lookback=252
- [x] Stage-2 sweep at 50/50 + 252 (`_om25_50_50_stage2.py`) — 19 configs
- [x] Universe sweep at 50/50 + 252 + top-25/buf-20 (`_om25_chosen_universes.py`) — 6 configs
- [x] OOS multi-window evaluation across universes (`_om25_chosen_universes_oos.py`)

## 3. Index data backfill — DONE

- [x] `scripts/backfill_gdf_indices.py` — 2009-2019 fetch, 134 indices
- [x] `scripts/extend_gdf_indices_to_today.py` — 2020-2026 fetch
- [x] All 135 NSE_IDX symbols on disk (11M, single GDF source)
- [x] `scripts/stitch_gdf_indices.py` written (not yet needed; using historical files directly)

## 4. Regime filter exploration — DONE

- [x] Post-hoc test: 200 DMA on 4 universe×cadence combos
- [x] In-engine test: 200 DMA, 4 indices, 36 configs
- [x] In-engine test: 100 DMA + 3-day confirmation hysteresis
- [x] **Regime as weight-lever** (`_om25_regime_weight_tilt.py`)
  - 76 configs: 2 univ × 2 cad × 3 indices × 6 weight pairs + 4 baselines
  - Winner: bull(50/50) → bear(0/100) on Nifty 250 biweekly + NIFTY 100

## 5. Year-by-year sanity check on chosen candidate — DONE

- [x] Year-by-year for tilt winner
- [x] Vs each major index (Nifty 50/100/200/250/500)
- [x] By-regime breakdown (bull vs bear stats)
- [x] No single year is a disaster; worst is 2011 at -11.6% (better than baseline -17.5%)

## 6. OM25 LOCKED IN (2026-05-10)

- [x] Final config documented in `RESULTS.md`
- [x] Performance: OOS 44.78% CAGR / 1.83 Sharpe / -36.6% DD
- [x] All sub-window pass criteria cleared
- [x] +24pp alpha vs NIFTY 200 over 17 years

## 7. TL25 retune — NOT STARTED

- [ ] Create `tasks/trend_leaders/experiments/_tl25_oos_retune.py`
- [ ] Stage-1: 7 weight variants (P/DD/M splits)
- [ ] Stage-2: ~60 configs around top-3 winners
- [ ] Universe + cadence + regime exploration mirroring OM25 process
- [ ] OOS multi-window evaluation

## 8. Write up RESULTS.md — OM25 done; TL25 pending

- [x] OM25 section: chosen config, all metrics, year-by-year, vs indices, regime breakdown
- [x] Survivorship-bias and other caveats noted
- [ ] TL25 section
- [ ] Cross-strategy comparison

## 9. Productionization (open)

- [ ] Adapt `scripts/build_om25_signals.py` to compute regime + apply tilt
- [ ] Adapt `scripts/backtest_om25.py` to support regime-tilt mode
- [ ] Wire regime data fetch into `scripts/run_daily_pipeline.py`
- [ ] Update `tasks/om25/README.md` with new locked-in stack
- [ ] Paper-trading window (3-6 months minimum) before live

## 8. Decide on next steps (post-results)

- [ ] User reviews RESULTS.md
- [ ] If pass + 40%/1.5 hit → discuss paper-trading
- [ ] If pass below target → discuss trade-offs vs production
- [ ] If fail → discuss alternative approaches

---

## Pre-flight checks (done)

- [x] `nse500_data_merged/` panel exists
- [x] `_clean_engine.py` has V2 OM25 score
- [x] `_clean_engine.py` extended with regime_panel + bear_exposure params
- [x] `nse500_data_historical/` raw GDF data committed
- [x] `indices_data_historical/` raw GDF index data on disk (uncommitted; consider committing)
- [x] Anti-overfit rules pre-committed in `PLAN.md`

---

## Pending technical TODOs

- [ ] Commit `indices_data_historical/` to git (~11MB) for reproducibility
- [ ] Add tests for `multi_window_oos_eval.passes_criteria` boundary cases
- [ ] Document the regime_panel/bear_exposure additions in `_clean_engine.py` docstring
