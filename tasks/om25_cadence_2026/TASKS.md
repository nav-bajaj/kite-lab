# Tasks

## Phase 1 — harness — DONE
- [x] 🤖 Task folder + PLAN with pre-registered pass criteria
- [x] 🤖 Vendor `multi_window_oos_eval.py` from the archive branch
- [x] 🤖 `_cadence_run.py` — production stack, cadence + universe as the only free dimensions
- [x] 🤖 `_summarise.py` — window metrics + post-tax overlay off `tasks/tax_study`

## Phase 2 — control validation — DONE ⚠️ FAILED AS EXPECTED-TO-PASS
- [x] 🤖 Run all 6 arms (nifty250 / nse500 × weekly / biweekly / monthly)
- [x] 🤖 Check bi-weekly Nifty 250 control against the archived winner curve
- [x] 🤖 **Control did not reproduce** (34.94% vs published 44.78%) — halted and diagnosed
- [x] 🤖 Attribution runs: `diag_nomem` (membership off), `diag_memstart` (archived start date)
- [x] 🤖 Replay archived trade log against today's panel → 8.6% of executions price differently
- [x] 🤖 Split the gap: −6.26pp price panel, −2.38pp membership, −0.01pp start date

## Phase 3 — analysis — DONE
- [x] 🤖 Cadence comparison on Nifty 250, pre- and post-tax
- [x] 🤖 Universe comparison, NSE 500 vs Nifty 250, all three cadences
- [x] 🤖 Drawdown timing / mechanism for the NSE 500 DD failure
- [x] 🤖 RESULTS.md with the reproduction failure stated up front

## Open — needs the founder 👤
- [ ] 👤 **Decide which price panel is correct.** `docs/portfolios.md` and the
      dashboard publish 44.78% CAGR / 1.86 Sharpe for OM25 v3. That does not
      reproduce on today's `nse500_data_merged`. Either the panel's new
      corporate-action state is right (→ republish the portfolio numbers) or it
      is wrong (→ `tasks/corporate_actions_fix` is load-bearing before any
      further research runs). Both `tasks/corporate_actions_fix` and
      `tasks/adjusted_price_series` are open and untracked.
- [ ] 👤 Whether the membership-masking history rewrite (−2.38pp on OOS_full)
      should be reflected in published figures — it is intended behaviour
      (`make_om25_tilt_score` docstring) but it moved a published number.
- [ ] 👤 Whether NSE 500 monthly is worth a replication run at all, given the
      standing "don't chase alternatives" stance.

## Explicitly not done
- No changes to `scripts/` or the pipeline. Nothing wired to production.
- No walk-forward or bootstrap — single realisation, ties under ~2pp.
- Bi-weekly opposite-phase arm not run.
