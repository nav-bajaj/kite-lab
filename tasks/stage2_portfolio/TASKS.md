# S2 portfolio - tasks

## Phase 1 - data spine (done)

- [x] 🤖 Build survivorship-free panel: reconstructed membership + ex-member
      backfill. 854 of 1,020 symbols have prices; calendar 2005-01..2026-08.
- [x] 🤖 Guard the two known panel traps - normalize/dedupe timestamped rows,
      mask ffill outside each symbol's real life. RISK: silent year loss.
- [x] 🤖 Confirm sector map coverage (484/854 = 57%; unmapped never capped).

## Phase 2 - signal (done)

- [x] 🤖 Stage-2 gate: 7-condition trend template + RS percentile + min stage age.
- [x] 🤖 Four pre-registered ranking variants (A_rs / B_quality / C_nofresh / D_blend).
- [x] 🤖 Loose hold gate for the asymmetric-gate test.

## Phase 3 - mechanics (done)

- [x] 🤖 Weight discipline: drift vs trim vs equal. Non-lever.
- [x] 🤖 Sector cap 0/3/4/6. RISK: theme concentration - this is the one lever.
- [x] 🤖 Stop ladder 0/20/25%. Non-lever - the gate exits first.
- [x] 🤖 Size 20/22/25. Non-lever.
- [x] 🤖 Exit buffer 10..400 and min-hold. Buffer >=40 is already gate-only.
- [x] 🤖 Asymmetric gate (strict entry, loose hold).

## Phase 4 - differentiation (done)

- [x] 🤖 TL25 v3 and L6 re-run on identical data, native and in S2 mechanics.
- [x] 🤖 OOS return correlation and month-end holdings overlap.
- [x] 🤖 Snapshot vs survivorship-free basis for both strategies.

## Phase 5 - open

- [ ] 👤 Founder call on whether S2 is worth a production slot at all.
- [ ] 🤖 Attribute the ~15pp survivorship gap through the PRODUCTION runners
      (`run_tl25_v3_portfolio.py --membership <reconstructed>`) rather than
      this task's engine, before any claim about the published figures.
      RISK: this touches how the track record is stated publicly.
- [ ] 🤖 Promoter-group concentration control. A sector cap does not catch the
      Adani complex (it spans five Zerodha sectors); the Jan-2023 and Nov-2024
      drawdowns were group events, not sector events.
- [ ] 🤖 Settle the ranking leg. IS prefers pure quality, OOS prefers RS, on
      both data bases. Needs a third window or a walk-forward, not a re-read
      of these two.
