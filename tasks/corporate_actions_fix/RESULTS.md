# Corporate-action fix — state (2026-08-23)

Tooling built and tested; repair execution pending a live Kite token
(trading morning) + founder sign-off on pipeline wiring. See PLAN.md
for root cause and design.

## Inventory (scan_cliffs.py, both price dirs)

**165 cliffs across 63 symbols** (`inventory.csv`), threshold ±28%:

- **DEFINITIVE corporate-action damage** (flip-flop signature or ≥40%
  step): the auto-repair set. Includes the live flip-flop cluster
  (ECLERX, IRB, ANANDRATHI, TRENT, BRIGADE-adjacent), ANGELONE's 1:10
  split (-90%), LICI, ZFCVINDIA, SPLPETRO, TRIVENI (two events, one
  on 2026-07-22 still live in the trailing window), BBTC, PIIND,
  ADANIENT-class demergers land in unclassified.
- **49 ambiguous rows / 26 symbols**: isolated ±28-40% ratio-matches.
  Includes KNOWN REAL events — the 2017-10-25 PSU-recap rally
  (BANKBARODA/BANKINDIA/PNB), IDEA's AGR swings, YESBANK March 2020.
  Never auto-repaired; the Kite refetch-compare is the arbiter.
- **58 unclassified rows**: real crashes and demergers. Kept as data;
  demergers need manual factors in corporate_actions.json (the VEDL
  pattern).

## Key design findings

1. **Ratio-snapping alone is not safe.** Real one-day rallies land on
   CA ratios (+33% ≈ undo 1:3, +46% PNB recap ≈ undo 1:2). The
   `definitive_ca_mask` discriminator (flip-flop pair OR ≥40%) removes
   most false positives, and genuine crash-bounce sequences (YESBANK
   -56% then +45%) can still fake a flip-flop — which is why no tool
   ever adjusts prices based on classification alone.
2. **The refetch is the final arbiter, by construction.** Kite's
   full-depth history reproduces real events identically and serves
   CA-adjusted prices. `refetch_history.py` compares fresh vs stored:
   "no_op: fresh matches stored" = real event; rows differing by ratio
   = CA re-base. False positives in the repair set cost API calls,
   never data.
3. The guard (report-only run today) catches exactly one live cliff in
   the trailing 20 sessions: TRIVENI 2026-07-22 -41.6% (bonus 2:3) —
   live, current, unrepaired damage feeding tomorrow's signals.

## Test status

`test_ca_lib.py`: 21 passed (detection, ratio classification incl.
tolerance bounds, flip-flop vs isolated discrimination, seam-ratio
recovery incl. mixed-regime refusal, clean-file checks).

## Remaining (runbook in PLAN.md)

- [ ] Trading morning: `refetch_history.py --probe-depth RELIANCE`,
      then `--from-inventory --apply` (locally AND on Railway volume).
- [ ] Founder: sign off guard wiring into run_daily_pipeline.py
      (between fetch and apply_corporate_actions) + whether --heal is
      automatic or report-only in production.
- [ ] Post-repair: re-run scan (expect definitive=0), then re-run
      dip-feed headline numbers without CLIFF_SYMBOLS exclusions.
- [ ] Promote ca_lib + guard from tasks/ into scripts/ once wired.
