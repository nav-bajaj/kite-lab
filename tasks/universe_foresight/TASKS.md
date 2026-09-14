# universe_foresight — tasks

Owners: 🤖 agent · 👤 founder

## Phase 1 — the ladder (done)

- [x] 🤖 Reproduce both book baselines on the honest store against MECHANICS.md
      (MM 25.2% / 1.15 / −27%, OM25 24.9% / 1.21 / −29% — exact)
- [x] 🤖 `lib/buckets.py`: b1, b1f, b2, b3 membership variants
- [x] 🤖 `lib/run_ladder.py`: MM, OM25 v4, L6 v2 across every rung
- [x] 🤖 Attribute the OOS CAGR gap to survivorship / early access / list narrowing

## Phase 2 — the honest alternative (done)

- [x] 🤖 `b4` point-in-time turnover universe, breadth-matched, no index reference
- [x] 🤖 Source turnover from the raw bhavcopy, not the adjusted panel
      (adjusted volume is share-count-scaled only, so the adjusted product
      understates a dividend payer's traded value by up to 8%)
- [x] 🤖 `lib/coverage.py`: size the panel-coverage hole in `b4`
- [x] 🤖 `lib/placebo.py`: random-exclusion control, 20 draws per book

## Phase 3 — the investability pool (done, founder follow-up)

- [x] 🤖 `b5`: the pool itself as the universe, no ranking, no breadth cap,
      swept over the turnover floor (Rs 1 / 2 / 5 / 10 cr)
- [x] 🤖 G3 sub-window gate on every (book, floor) — separates OM25 from MM
- [x] 🤖 Sector-cap ablation: the cap is worth ~4pp narrow, ~0 wide, and is not
      manufacturing the wide result
- [x] 🤖 Size the panel-coverage hole at pool breadths (20-37% from 2021)

## Phase 4 — panel extension (done)

- [x] 🤖 `panels/pr_full`: 2519 adjusted symbols. The extension was free —
      `prices/adjusted_pr` already held them and `panels/pr` is a filtered copy,
      byte-identical per file, so pr_full is the same files symlinked whole
- [x] 🤖 Re-run `b5` on it (`lib/wide_full.py`, own runs dir since cfg_id does
      not include the panel). Coverage of the investable set 65-85% -> 95-100%
- [x] 🤖 Validate the swap: `b0` is identical on both panels for all three books
- [x] 🤖 **Result reverses.** The pool no longer beats the index universe on any
      book at any floor; the addendum's +8.6pp was entirely the coverage hole

## Phase 5 — NSE 500 point-in-time (done)

- [x] 🤖 Locked MM and OM25 v4 on nse500 PIT, plus a turnover floor INSIDE the
      index, plus satellite sleeves (`lib/nse500.py`)
- [x] 🤖 MM fails G3 and satellites lose, reproducing mm_rebuild §4/§8/§9/§14
- [x] 🤖 OM25 v4 on nse500 beats what shipped on full OOS (+1.9pp, gates passed)
      — a comparison §22 never ran, since it fixed the universe at nifty250
- [x] 🤖 Recency check kills it: rolling 3y Sharpe 2.38 -> 0.73, trailing 3y
      15.3% / 0.57 against nifty250's 30.2% / 1.34
- [x] 🤖 New finding: a liquidity floor inside NSE 500 makes both books worse,
      so the return partly lives in exactly the tail a product wants to exclude

## Phase 7 — "once in NSE 500, always eligible" (done — the live candidate)

- [x] 🤖 Founder's construction: eligible from first index entry, never removed.
      No foresight; immune to the panel limitation by design (`lib/oncein.py`)
- [x] 🤖 Verified identical on the narrow and full panels, as the design implies
- [x] 🤖 OM25 v4: 30.4% / 1.43 / −29% vs shipped 24.9% / 1.21 / −29%, G3 PASS.
      MM fails G3 as everywhere else
- [x] 🤖 Rolling 3y Sharpe never below 1.02 — no NSE 500-style decay
- [x] 🤖 Delisting robustness: ZERO exits on a delisting date; the stop and rank
      exit clear decaying names first. D-9 optimism does not touch the result

## Phase 8 — diagnostics (done)

- [x] 🤖 8a Why not MM: risk not return — same CAGR, +12% vol (+38% in 2016-19);
      MM churns the ex sleeve (63d median hold vs OM25's 90d) (`lib/diagnose.py`)
- [x] 🤖 8b Why the recent fade: the never-delete pool grows 46% -> 60% of the
      universe and its trip quality rots (win 62-70% -> 39-47%, p90 +182% -> +40%)
- [x] 🤖 8c Grace-period refit: NEGATIVE and non-monotonic (`lib/decay.py`)
- [x] 🤖 8d Announcement date: no effect, slightly negative for MM; bites only
      22 of 389 buys because the momentum RANK binds, not eligibility
      (`lib/announce.py`). Underpowered below ~±1.5pp; 2020-> only

## Phase 9 — refit with the recent window held out (done)

- [x] 🤖 Pre-registered protocol in `lib/refit.py`; 60-cell grid on BOTH
      universes so the narrow book gets the same number of shots
- [x] 🤖 Selection on 2016-2023 only: once-in's grid MEDIAN Sharpe (1.45) beats
      nifty250's grid MAX (1.29); 59/60 cells clear the gates vs 27/60
- [x] 🤖 Hold-out 2024-> run once (`lib/holdout.py`): **shipped OM25 v4 wins
      outright** (28.3% / 1.21) and every once-in variant loses (0.86-0.98)
- [x] 🤖 Control: the same refit made nifty250 WORSE out of sample (fit 1.29 ->
      hold-out 0.97 against shipped's 1.21) — the selection machinery itself does
      not generalise at this trial count

## Phase 10 — 12-month demotion window, held out (done)

- [x] 🤖 `lib/decay12.py`, same sealed protocol. The 60-cell grid's winner IS the
      shipped configuration (mix 0.5 / n25 / b20 / s5), so this is a clean
      universe test with no parameter overfitting available
- [x] 🤖 Hold-out 13.5% / 0.47 / −32% — the WORST of everything tested, despite
      the best fit-window Sharpe (1.66)
- [x] 🤖 It fixed 2025 as designed (−3.0% vs once-in's −12.0%) and destroyed 2024
      (+31.3% vs +65.7%): the ex-member sleeve is one exposure, not separable by age
- [x] 🤖 Fit-window rank is EXACTLY inverted out of sample, 4 constructions for 4

## Phase 13 — capped dropped-name sleeve (done, rejected)

- [x] 🤖 `lib/satellite.py`: core Nifty 250 PIT + 16/20/24% reserved for dropped
      names, sealed hold-out. Every variant loses on BOTH windows
- [x] 🤖 Clarifies Phase 7: `nifty250 once-in` (20.9% / 1.04) is far worse than
      `nse500 once-in` (33.9% / 1.63) — the headline was the 251-500 band, not
      the demotion-recovery mechanism
- [x] 🤖 Premise tested directly: drop -> re-inclusion trips show +40.5% median
      excess, 70% win, back-loaded (13% of it in the first half of the gap)...
- [x] 🤖 ...but only 33% of dropped names EVER come back. Unconditionally the
      median dropped name is **−28.2pp vs Nifty 500 over 3 years, 35% win rate**;
      the never-returning 67% are −37.2pp. Re-inclusion IS the surge, so the
      cohorts cannot be told apart at the drop date

## Outcome — closed

- [x] Do not adopt. MECHANICS unchanged; both books keep Nifty 250 PIT.

## Superseded — plans that later phases retired

Kept as a record of what was planned; none of it is open work.

- *Evaluate the once-in candidate properly* (G5 walk-forward, capacity at
  Rs 5-10 L, governance screen, sign-off) — retired by Phase 9. The candidate
  failed the hold-out, so there was nothing left to validate.
- *The floored-variant panel discrepancy* (29.3% narrow vs 26.3% full) — never
  resolved, and no longer matters: only the no-floor once-in number was ever
  quoted, and once-in is rejected.
- *Turnover-proportional slippage* (planned as Phase 6, never numbered in
  RESULTS.md) — was the gate for trusting wide-universe results. Phase 5b
  narrowed why it matters: today's NSE 500 has no illiquid tail, so this is a
  question about the honesty of 2016-2019 backtest years, not about whether the
  current index is investable. **This is the one genuinely open item below.**
- *A retune for a wide universe* — done in Phase 9, negative.

## Genuinely open

- [ ] 🤖 Turnover-proportional slippage in the engine. Affects the honesty of
      2016-2019 backtest years across every book, not just this folder's
      candidates. Not required by anything currently in production.
- [ ] 👤 A fundamentals feed (open since `tasks/breakout_calls_2026`). Phase 13b
      identified it as the only untested way to separate the 33% of dropped names
      that recover from the 67% that do not — and Phase 1's finding that
      governance screening has no measurable prize lowers its expected value.

## Not done, and why

- **A fundamentals / governance screen.** Needs the fundamentals feed that
  `tasks/breakout_calls_2026` left open, and finding 1 of the main results says
  the obvious version of it has no prize. Out of scope here — this folder only
  tested universes computable from price and volume.
- **TL25 and COMBO.** The three books tested span both universes and both score
  families and already disagree with each other in the informative way.
