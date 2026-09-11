# Fortnightly data-quality checks (founder, 2026-09-11)

Runs every second Monday at 07:00 IST (before the morning login), once the new books are live;
also on demand from the admin jobs page. Output: `reports/data_quality/<date>.md` (committed
summary) plus a status line on `/api/freshness`. Each check states what it compares, the
threshold, and what a failure does. Thresholds are the spine's measured tolerances, not
guesses; tighten only with evidence.

| # | Check | How | Threshold | On failure |
|---|---|---|---|---|
| 1 | **Basis reconciliation** | For every current point-in-time member and every name either book holds: bhavcopy close × CA factors vs Kite adjusted close, last 60 sessions, ratio should be constant | ratio step > 0.4% on any day without a filed event (`verify_kite_adjustment` tolerance) | list the symbol and day in the report; the symbol goes on the re-pull list; if the name is held, the morning review must clear it before the next rebalance |
| 2 | **Kite band detector, full history** | The same ratio test over the entire Kite series (the nightly covers 30 days only) | any unexplained step | full re-pull of the symbol; if the step persists it is a missing filing — add the event |
| 3 | **Coverage** | Every member on every session of the last 14 days has a bhavcopy row; every held name has a Kite row | one missing session per symbol (a suspension is legitimate; two in a row is not) | stale-tail listing; suspended names flagged to the book runner (price carried, no new entry) |
| 4 | **Calendar** | Store sessions vs the NSE trading calendar (holidays file, special Saturday/Sunday sessions) | any session missing or extra | fetch the missing day; a not-published day older than 3 days is an NSE gap to record |
| 5 | **Corporate-action completeness** | NSE CA feed for the last 45 days and the next 30: every split / bonus / rights / demerger filing has a row with a factor; every ex-date in the coming 30 days is queued | any price-relevant filing without a row | parse and add before the ex-date; the nightly's look-ahead fetch should make this zero |
| 6 | **Bad prints** | Spike-and-revert rows in the last 14 days where Kite disagrees with the bhavcopy | zero expected | quarantine the row (the loader masks it), keep the raw file |
| 7 | **Membership integrity** | `members_asof` = 250 / 500 / 100 / 50 on every session; rename edges vs `SYMBOL_ALIASES`; any NSE reconstitution announcement not yet staged | any count off by one; any announced event without a staged row | fix the membership file before the effective date; the reconstitution runbook |
| 8 | **Book reproducibility** | Recompute each live book from its lock date on today's store and diff against the stored track: equity path, trades, holdings | any difference before the last 20 sessions | the store rewrote history — find the changed input (CA table row, price file, membership row); nothing is published until explained |
| 9 | **Signal stability** | Recompute the last three rebalances' top-45 lists and bear/regime state from today's store; compare with what was traded | any name that moved across the entry or exit rank, any regime day that flipped | a rewrite of an input since the rebalance; list it — usually a late CA filing |
| 10 | **Benchmarks** | NIFTY 100 / 500 / Midcap 150 / LargeMidcap 250 closes vs NSE's published index values, last 14 days | > 0.05% on any day | refetch; a persistent gap is a series-definition issue |
| 11 | **Sector map** | Every current member has a sector; new entrants since the last check labelled | any unlabelled member | label from the NSE list; the cap treats unlabelled names as unconstrained, which is the wrong default for a live book |
| 12 | **Nightly health** | The last 14 `qa/nightly_*.json`: runs completed, Kite error share, gate status | any night missing; Kite error share > 5% on any night; three flagged nights in a row | page; the morning review has been skipped |
| 13 | **Snapshot integrity** | sha256 of every price file vs the manifest; manifest vs directory listing | any mismatch | a file was edited outside the pipeline — restore from the nightly backup |

## Notes

- Checks 1, 2 and 8 are the ones that catch the production defect discussed on 2026-09-11 (a
  15-day adjusted band inside a raw series): 1 and 2 see the band as a ratio step, 8 sees it
  as a rewritten track.
- Check 8 is the spine's `audit_immutability.py --strict` adapted to the snapshot model;
  checks 1, 2, 6 reuse `verify_kite_adjustment.py` and `qa_report.py`; 7 reuses the
  reconstitution tooling; the rest are new and small.
- Scheduling: APScheduler cron `day_of_week=mon, hour=7, minute=0` with a fortnight guard
  (run only when ISO week number is even), registered like `master_store_refresh`.
- Cost: the full-history ratio test (2) over ~1,000 Kite series is a few minutes; check 8 is
  two portfolio recomputes (~10 s each). The whole run should finish inside 15 minutes.
