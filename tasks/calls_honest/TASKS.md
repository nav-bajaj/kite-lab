# calls_honest — tasks

## Phase 1 — port (done)

- [x] 🤖 Stage-2: gate, tiered hold gate, RS + un-extension score, engine with exit confirmation, from branch `stage2_portfolio`.
- [x] 🤖 Dip feed: 126-day vol-adjusted momentum rank, 5-day dip entry, rank < 0.35 exit, 20% trailing stop, cap 25, from `tasks/dip_vs_breakout_calls/experiment.py`.
- [x] 🤖 Both on master-store panels with point-in-time membership (nifty250, nse500). RISK: rank definitions on an all-ever panel — resolved as rank across members, held ex-members ranked against members.

## Phase 2 — runs (done)

- [x] 🤖 4 runs, 2010-01-01 → 2026-09-09, frozen parameters.
- [x] 🤖 Self-checks: truncation at 2019-06-28, execution lag, S2 engine vs production engine.
- [x] 🤖 Sensitivity of the one interpreted rule (RS percentile basis). Reported, not adopted.

## Phase 3 — report (done)

- [x] 🤖 RESULTS.md in the om25/mm format, with the earlier biased numbers alongside.

## Open

- [ ] 👤 Founder read: neither strategy beats the MM base rows on Sharpe; is the dip feed's trade shape (11-12% expectancy, 45-47% win rate) still the calls product?
- [ ] 🤖 If any calls product goes forward: validity protocol (`tasks/insight_engine/pattern_validity_study.py`) on the honest store.
