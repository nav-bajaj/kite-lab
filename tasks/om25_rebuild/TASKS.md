# Tasks

Owners: 👤 founder · 🤖 agent.

## §0 — pre-committed pass criteria — SIGNED 2026-09-10, frozen

| # | Criterion | Value |
|---|---|---|
| G1 | IS Sharpe (rf 5%), 2006-2015, after deflation for candidates tried | ≥ 0.9 → **≥ 0.8 raw, relaxed by the founder 2026-09-10 after the in-sample close at 616 trials** (deflated value reported alongside; at 616 trials with observed sd 0.21 the deflation is 0.66, so no deflated value can pass) |
| G2 | OOS Sharpe, 2016-today | ≥ 0.9 |
| G3 | OOS sub-window Sharpe, each of 2016-19 / 2020-22 / 2023-26 | ≥ 0.6 |
| G4 | OOS maximum drawdown | no worse than −40% |
| G5 | Walk-forward Sharpe within this of the static OOS Sharpe | 0.2 |
| G6 | Parameter count, all-in (score weights, regime, N, buffer, cadence, lookback, overlay ROC N, confirm, bear exposure, redeploy) | ≤ 10 (raised from 8 by the founder 2026-09-10 to admit the overlay; counts everything searched) |
| G7 | Turnover reported; no gate, but a candidate that wins only on turnover-blind metrics is flagged |  |
| G8 | Minimum return (added by the founder 2026-09-10: "20-25% range"). Recorded at the floor of the range pending the founder's number. CAGR over OOS 2016-today and over 2006-today; IS CAGR reported against the benchmark (10.9% price return 2006-2015) but not gated, because a 2008-in-window decade floor is an index-relative question | ≥ 20% |

## §1 — retrieve the ROC regime test 🤖

- [x] Located: `tasks/portfolio_risk_2026/` on `beta_gtm_mvp`; definition
      and result recorded in BRIEF.md (sign of N-session ROC of NIFTY 100,
      confirm-days hysteresis, best cell 31/3 on the biased universe)
- [x] 👤 ROC grid N ∈ {15, 21, 31, 42} × confirm ∈ {2, 3, 5}
- [x] 👤 Exposure overlay: later, out of scope here
- [x] 👤 Market for up/down days: (b) equal-weight signal-date members over the window

## §2 — harness 🤖

- [ ] `lib/score.py`: UC, CR, blend — per the OM25 v3 construction minus the
      50-up/50-down rule; positive-return filter kept as a switch
- [ ] `lib/regime.py`: ROC of the regime index with confirmation hysteresis;
      "one regime" = the panel is ignored
- [ ] `lib/run.py`: one candidate → equity/trades/exits on the master store,
      via `_clean_engine.run_strategy`, no weight cap, no stops
- [ ] `lib/windows.py`: IS / OOS / sub-windows / walk-forward evaluator,
      pass-criteria check, candidate counter for deflation
- [ ] Smoke test: the old OM25 v3 configuration reproduces
      market_data_spine's Phase 6 number when its constraints are re-enabled

## §3 — build, IS only 🤖

- [ ] 3a score × universe (6 runs)
- [ ] 3b regime: one vs two, ROC parameters (small grid) on 3a's winner
- [ ] 3c top-N / exit buffer / cadence grid
- [ ] 3d lookback / min_obs
- [ ] 3e exposure overlay: ROC grid × bear exposure {75, 50, 25, 0} × return filter, both universes, ≤25 names
- [ ] Deflate; record every run in RESULTS.md with its number

## §4 — OOS and walk-forward, opened once 🤖👤

- [x] Surviving configuration per universe → OOS, sub-windows, walk-forward — DONE 2026-09-10, all five fail G2/G3/G8, pass G4/G5
- [ ] 👤 Decide the universe and whether the book ships — evidence complete after §4b (adaptive Nifty 250 monthly, 5-year refit: 21.6% / 0.90 / −34.6% chained OOS)

## Done

- [x] Task opened with the founder's constraints verbatim (BRIEF.md)

## §3f/§3g — cadence, redeploy, re-entry on flip — DONE 2026-09-10
Redeploy switch a no-op for full-exit books (documented); re-entry on the
bull flip implemented in lib/run.py (`reenter_on_flip`) and worth +0.29 on
LM 250 monthly. In-sample closed at 616 trials; G1 and G8 fail; OOS not
opened. Awaiting the founder's decision.

## Founder decisions 2026-09-10 (after §3h)
- **In-sample window moved to 2010-01-01 → 2015-12-31.** 2008 and the 2009
  recovery are out of the gated window; the book is judged fully invested.
  The 2006-2015 result (fails G1/G8 for every configuration) stands on the
  record as the reason.
- An overlay is still required for "anything similar in future", but the
  ROC exposure overlay is not it (costs 5-15pp a year outside 2008). The
  founder's proposal: an indicator of the *strength of momentum* across
  the index's stocks; when it declines or drops below a threshold, cut
  exposure. Explored by an agent as §3j (brief in lib/BRIEF_3j.md).
- Cadence grid from 2010 (§3i): weekly, biweekly entry+exit, biweekly
  entry / weekly exit, monthly, on both universes.
- G8 number still to be fixed by the founder (20% recorded).

## §4 opened — founder decisions 2026-09-10
Both universes stay open. Lookback: 12 months on Nifty 250, **6 months on
NSE 500** (founder choice on §3k; recorded as a choice, the window shows
no plateau). Cadence: monthly and biweekly, entry and exit together.
Candidates fixed before any 2016+ number was computed: A N250 monthly,
B N250 biweekly, C N500 monthly, D N500 biweekly, all fully invested, and
E = A with the §3j breadth overlay (200-DMA breadth < 0.30, confirm 3,
full exit, flip re-entry) — included at the researcher's initiative so the
overlay question is answered in the same single opening; the founder had
not ruled on it. Walk-forward refits lookback only (63/126/189/252) on
the trailing ten years, chained yearly 2016 → today. G8 stays at 20%.
