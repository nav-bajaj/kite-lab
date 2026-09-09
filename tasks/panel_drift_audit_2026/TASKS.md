# Tasks

## Phase 1 — L6 v2 — DONE
- [x] 🤖 Run L6 v2 via the production runner, membership ON and legacy
- [x] 🤖 Compare against the published 2020-07-10 -> 2026-02-02 figure
- [x] 🤖 Establish which arm is archive-equivalent (membership ON — seeded@1900
      == May-2026 snapshot, 500/500 on NSE 500) and RETRACT the first reading
- [x] 🤖 Localise the drift by era on OM25 — confined to 2017-2019
- [x] 🤖 Rule out coverage gaps (row counts/year, duplicate dates, phantom timestamps)
- [x] 🤖 Quantify inclusion bias in the legacy path on both strategies
- [x] 🤖 Correct the mis-attribution in tasks/om25_cadence_2026/RESULTS.md

## Phase 2 — remaining portfolios — NOT STARTED
- [ ] 🤖 TL25 v3 reproduction check vs archive-branch curve (shares OM25's window — expected to fail)
- [ ] 🤖 COMBO Defensive reproduction check
- [ ] 🤖 Inclusion-bias measurement for both

## Phase 3 — decide — needs the founder 👤
- [ ] 👤 **Is the current 2017-2019 panel right or wrong?** Everything downstream
      waits on this. If right: republish OM25 v3's figures. If wrong:
      `tasks/corporate_actions_fix` blocks all research runs touching pre-2020.
- [x] ~~Whether to restate published figures for inclusion bias~~ — **moot**.
      Membership ON reproduces the old universe exactly; nothing to restate on
      that account. See RESULTS.md §1.
- [ ] 👤 Whether client-facing copy needs a "figures restated" note — depends
      entirely on the panel decision above, not on membership.

## Explicitly not done
- No production changes. Both L6 runs used `scripts/run_l6_v2_portfolio.py` unmodified.
- No attempt to determine which panel state is correct.
