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

## 4. Regime filter exploration — IN PROGRESS

- [x] Post-hoc test: 200 DMA on 4 universe×cadence combos (`_om25_regime_filter_test.py`)
- [x] In-engine test: 200 DMA, 4 indices, 36 configs (`_om25_regime_in_engine.py`)
  - In-engine numbers ~10pp lower CAGR than post-hoc — friction is real
- [x] In-engine test: 100 DMA + 3-day confirmation, same 36 configs (`_om25_regime_100dma_3conf.py`)
  - Big improvement: +0.1 to +0.34 Sharpe vs 200 DMA
  - Two strong candidates: NSE 500 biweekly + NIFTY 200 + 25% bear (Sharpe 2.07 / 37.7% / -25.8%); NSE 500 biweekly + NIFTY 50 + 0% bear (40.3% / 1.94 / -27.9%)
- [ ] **NEXT — Regime as weight-lever**: regime tilts UC/CR weight blend instead of cash on/off. Strategy stays fully invested; regime just biases stock selection.
  - [ ] Build `tasks/om25/experiments/_om25_regime_weight_tilt.py`
  - [ ] Closure score: bull weights vs bear weights; lookup regime per signal date
  - [ ] Sweep: pairs like {(70/30, 30/70), (60/40, 40/60), (70/30, 0/100), (60/40, 0/100)}
  - [ ] Same regime signal: 100 DMA + 3-day confirmation
  - [ ] Same universe candidates: NSE 500 biweekly, Nifty 250 biweekly
  - [ ] Same indices: NIFTY 50 / 100 / 200

## 5. Year-by-year sanity check on top candidates

- [ ] Year-by-year breakdown for each top candidate (Candidate A, B, regime-tilt winner)
- [ ] Verify no individual year is a disaster
- [ ] Cross-check IS year-by-year vs OOS to look for IS-specific behavior

## 6. TL25 retune — NOT STARTED

- [ ] Create `tasks/trend_leaders/experiments/_tl25_oos_retune.py`
- [ ] Stage-1: 7 weight variants (P/DD/M splits)
- [ ] Stage-2: ~60 configs around top-3 winners
- [ ] Universe + cadence + regime exploration mirroring OM25 process
- [ ] OOS multi-window evaluation

## 7. Write up RESULTS.md — NOT STARTED

- [ ] OM25 section: chosen config, all metrics, year-by-year, vs production
- [ ] TL25 section: same
- [ ] Cross-strategy comparison
- [ ] Survivorship-bias caveat
- [ ] Recommendation per strategy

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
