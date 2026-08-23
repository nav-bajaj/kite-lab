# Corporate-action fix — state (2026-08-23, post-repair)

**LOCAL REPAIR EXECUTED AND VERIFIED** (evening 2026-08-23, after the
local daily pipeline run). Production (Railway volume + DB) NOT yet
touched — see "Production status" below. Tooling docs in PLAN.md.

## Repair log (local)

1. Deep Kite refetch (`refetch_history.py --apply`, start 2005-01-01):
   62/63 damaged symbols rebuilt in BOTH dirs from Kite's adjusted
   history (depth probe: RELIANCE serves from 2005-01-03). JBCHEPHARM
   unfetchable (delisted) — stored data left as-is. Merged histories
   now extend to 2005 for most repaired symbols. Pre-repair snapshots
   of all 126 files in `backup_pre_repair/` (rollback = copy back +
   revert data/corporate_actions.json).
2. Six events Kite itself does not adjust, fixed via market-derived
   continuity factors (`demerger_factors.json` + `apply_factors.py`):
   VEDL demerger 2026-04-30 (x0.7150 — the old JSON entry 0.3834/773.6
   was WRONG), TRIVENI demerger 2026-07-22 (x0.6150), SPLPETRO
   unadjusted bonus 2022-06-07 (x0.5271, Kite's own instrument serves
   it raw), ADANIENT demerger 2015-06-03 (x0.5808; Kite's ex-day OPEN
   555.8 is corrupt, left documented), MFSL 2016 restructuring
   (x1.4774) and 2007 split (x0.2054), CGPOWER vendor splice
   2015-01-01 (x2.9067). VEDL's corrupt first 19 rows (Jan 2005)
   trimmed. Residual ex-day steps are real market moves (-6% to +5%).
3. `data/corporate_actions.json` rewritten (local, uncommitted-to-prod):
   corrected VEDL + added TRIVENI, SPLPETRO so the pipeline's apply
   step protects the live dir against overlap-refetch regressions.

## Verification matrix (all pass)

- Cliff scan: definitive rows 14 -> **3**, and all 3 are refetch-
  verified REAL events (PNB +46.2% 2017-10-25 recap day; YESBANK
  +45.2% 2020-03-16 rescue rally) — data, not bugs.
- Daily guard: trailing 20 sessions clean.
- Live vs merged: max deviation 0.000000 on all shared dates for
  spot-checked repaired symbols (TRENT, VEDL, ECLERX, ANGELONE,
  TRIVENI).
- Loaders: merged panel loads 6086x500 (2005-01-03..2026-08-21); live
  panel 1650x534. Headers/date format unchanged.
- Control: untouched symbols (RELIANCE) byte-identical to pipeline
  output; only the 63 inventory symbols were written.
- ca_lib tests: 21/21.
- Live-position fix: VEDL (held by OM25 v3) now on one consistent
  basis; 126d return moves +6.5% -> +9.7% (was mis-ranked).

## Universe membership audit (2026-07-15 refresh)

All 34 additions have live+merged files (IPO-era names correctly start
at listing; deep pre-listing history impossible). All 34 dropped names
still fetch daily (grandfather rule) except the three known
merger/delist cases: GSPL (last 2026-05-11), GUJGASLTD (2026-05-27),
JBCHEPHARM (2026-07-14) — expected, previously flagged.

## Production status — NOT yet repaired

- Railway volume still holds damaged data, including VEDL on the wrong
  0.3834 basis with a sidecar key that will BLOCK the corrected JSON
  from re-fixing it (threshold logic sees "already applied"). Railway
  repair = run refetch_history there (or delete flagged CSVs + let the
  fetch rebuild), NOT just a JSON deploy.
- **The next local pipeline run will compute signals on repaired data
  and push DB sync + cloud upload — that IS production propagation.**
  Founder should review before the next run; rollback available.

## Completed follow-ups (2026-08-23 evening, founder-approved plan)

- [x] Demerger triage: JSL 2015 (x0.4054), CGPOWER 2016 Crompton
      demerger (x0.3413; ex-day also had a real -17% crash, factor uses
      open-continuity), TATACHEM 2020 (x0.4377), ABFRL 2025 (x0.4815)
      applied to both dirs; TATACHEM + ABFRL mirrored into
      data/corporate_actions.json (they straddle the live dir). COHANCE
      2020-03-24 adjudicated REAL (refetch matched stored) — no factor.
      Final scan: definitive rows = PNB + YESBANK only (verified real).
- [x] Guard promoted to production code (LOCAL commit, not deployed):
      data_pipeline/corporate_actions.py + tests/test_corporate_actions.py
      (21 cases) + scripts/reconcile_price_integrity.py, wired into
      run_daily_pipeline.py BEFORE the fetch step (deleted files rebuild
      in the same run; non-fatal on guard failure). Heal queue sidecar:
      nse500_data/.merged_rebase_queue.txt.
- [x] sync_insights_panels: "no new splits" assumption replaced with a
      live-vs-merged divergence check (MEDIAN deviation > 2% over last
      10 shared dates -> skip append + queue for re-base). Median-based
      because isolated small diffs are Kite candle revisions
      (preliminary-vs-final, up to ~0.8% observed) — expected noise, and
      they persist in merged by design (append-only contract kept).
- [x] Dip-feed re-run on healed full universe (NO_CLIFF_EXCLUDE=1):
      headline arm 36.9% CAGR / 1.77 Sharpe / -35.9% DD, 66 calls/yr
      (vs 37.8 / 1.65 / -34.6, 58.5/yr on the excluded universe) —
      conclusions unchanged, finding robust to the repair.

## Remaining (production, gated)

- [ ] Railway repair: run refetch_history + apply_factors on the
      Railway volume (its data still damaged; VEDL on the wrong 0.3834
      basis with a sidecar key that blocks JSON-only correction).
- [ ] Deploy the guard wiring (this branch's commits) to the Railway
      service after founder review.

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
