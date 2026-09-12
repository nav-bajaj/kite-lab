# TESTS_DATA — integrity tests for the master store the rebuilt books read

Scope: `data/master` exactly as `scripts/rebuilt_books.py` consumes it — the price-return
panel view, the point-in-time Nifty 250 membership, the NIFTY 100 regime series, the sector
map, the corporate-action table behind the adjusted view, and the manifests and QA files that
say whether the store is intact. Every test here is **local and offline**: it reads files
already on disk and needs no Kite session, no NSE fetch and no network.

Relationship to `tasks/production_port_2026/DATA_QUALITY_CHECKS.md`: those 13 checks are the
fortnightly **operational** run — they compare the store against live sources (Kite, the NSE
CA feed, NSE's published index values, the nightly job history). This suite complements them
by checking the store's **internal consistency**, which is what a book actually reads. Where a
fortnightly check has a purely local half, that half is implemented here and the check number
is cited (D-15/D-16 ⊂ check 1/2, D-19 ⊂ check 6, D-24/D-25 ⊂ check 7, D-31 ⊂ check 10,
D-36 ⊂ check 11, D-39/D-40 ⊂ check 13, D-42 ⊂ check 12). Nothing here re-runs a fortnightly
network check.

## Conventions

- **Severity `hard fail`** — the test asserts and goes red. A red test means a book run on
  this store is wrong or will crash.
- **Severity `warn`** — the test emits a `StoreWarning` carrying the count and the first names
  involved, and asserts only against a **generous cap** calibrated on the 2026-09-12 store
  (stated per test). It PASSES while the count is under the cap; the cap exists so a tenfold
  regression still turns the suite red. Run with `-W default::UserWarning -rw` to see the
  warning text in the pytest summary.
- **Book scope.** Several tests are hard only for the names that matter to `mm_v1` / `om25_v4`:
  a **current member** is a symbol in `membership/nifty250.csv` live on the store's latest
  session, and the **book data era** is `>= 2014-01-01` — a 252-session lookback skipped 21
  sessions back from the books' 2016 record start reaches to about 2014-11, so 2014-01-01 is
  the conservative boundary. Outside that scope the same condition is reported as a warning.
  The brief's stronger scoping ("hard-fail only if a currently *held* name is affected") needs
  the runner's holdings; no `data/mm_v1_portfolios/` or `data/om25_v4_portfolios/` output
  exists locally yet, so the holdings-scoped variant is a single skipped test (D-38).
- **Accepted facts, not failures.** The store spans 2005-01-03 onward; the view the books read
  is price-return, so dividends are deliberately *not* adjusted; a delisted name ends at its
  last traded price; 1,478 of 2,519 symbols have no Kite series, so no cross-check is possible
  for them; the nightly gate stands at `flagged` on a standing list (about 30 unexplained Kite
  steps in 30 days). None of these is asserted against.
- **Cost.** One pass over `prices/adjusted_pr` + `prices/adjusted_tr` + `prices/bhavcopy`
  (1.6 GB), one pass over `prices/kite`, one panel load, one sha256 sweep. 42 tests in ~45 s.
- **Where the readers live.** `tests/_store.py`, not `tests/conftest.py` — `conftest.py` in
  that folder belongs to the book behaviour suite (`TESTS_BOOKS.md`), so the data suite keeps
  its session-level caching in its own module (an `lru_cache` on a zero-argument reader is
  memoised for the whole pytest session). The two suites share the folder and nothing else.
- **How to run.**
  `.venv/bin/python -m pytest tasks/book_verification_2026/tests/test_data_*.py -p no:cacheprovider -W "default::UserWarning" -rw -q`

## A — file and schema integrity

### D-01 — every adjusted_pr file parses with the expected schema
**Checks** all 2,519 `prices/adjusted_pr/*.csv` read as CSV and carry exactly
`date,open,high,low,close,volume,traded_as,factor` in that order.
**Method** `pd.read_csv` per file in the session fixture; compare `list(df.columns)`.
**Pass** zero parse errors, zero column-set deviations, zero empty files.
**Severity** hard fail.
**Means** the panel loader would either skip the symbol silently (no `close` column) or raise;
a book would run on a smaller universe than its config says.

### D-02 — dates are midnight-normalised, unique and strictly increasing
**Checks** no intraday timestamps, no duplicate session rows, no out-of-order rows.
**Method** per file: `(d.dt.normalize() != d).sum()`, `d.duplicated().sum()`,
`(d.diff() <= 0).sum()`.
**Pass** all three zero for every symbol.
**Severity** hard fail.
**Means** `load_price_panels` pivots on `date`; a duplicate raises on pivot, and a timestamped
row becomes a phantom calendar day that `rolling()` silently eats (the panel-calendar trap,
`reference_panel_calendar_trap`).

### D-03 — closes are finite and strictly positive
**Checks** no NaN, no zero, no negative close in the adjusted view.
**Method** `np.isnan(c).sum()` and `(c <= 0).sum()` per file.
**Pass** zero on both, every symbol.
**Severity** hard fail.
**Means** a zero close makes `pct_change` infinite and poisons every score, vol and weight
that touches the symbol; a NaN inside a series (as opposed to before listing) breaks the
`min_obs` count the books gate entry on.

### D-04 — OHLC bars are internally consistent
**Checks** `high >= low`, `low >= 0`, and `open`/`close` inside `[low, high]`.
**Method** per file, with tolerance `2e-4 + 1e-6 * |close|` — the adjusted view is written
rounded to 4 dp, so a bar can sit one tick outside its own range without being wrong.
**Pass** zero violations beyond tolerance.
**Severity** hard fail.
**Means** the books' trade price is the OHLC/4 mean; a bar whose open is outside its range is
a corrupted row and the fill price is fiction.

### D-05 — volumes are finite and non-negative
**Checks** the volume column after the share-count rescaling `build_adjusted` applies.
**Method** `np.isnan(v).sum()`, `(v < 0).sum()`.
**Pass** zero on both.
**Severity** hard fail.
**Means** a negative volume means the inverse share-count factor was applied wrongly, which
implies the price factor beside it is suspect too.

### D-06 — the factor column is usable and ends at 1.0
**Checks** `factor` finite and `> 0` everywhere, and exactly `1.0` on each series' last row.
**Method** per file; `abs(factor[-1] - 1) <= 1e-9`.
**Pass** every symbol.
**Severity** hard fail.
**Means** the last row is by construction unadjusted (`build_adjusted` only multiplies rows
*before* an ex-date). A last factor other than 1.0 means the adjusted file and the raw file
have drifted apart — today's close would not be the close that traded.

### D-07 — panel views mirror their source and are portable
**Checks** for `panels/pr` and `panels/tr`: the `<SYM>_day.csv` link set equals the
`prices/adjusted_<view>` listing, every link resolves to an existing file, and every link is a
**relative** symlink. Any further view directory under `panels/` is checked the same way but
reported, not asserted.
**Method** `Path.glob`, `is_symlink`, `os.readlink` (absolute target = not portable),
`resolve().exists()`.
**Pass** sets equal, zero broken links, zero absolute targets in `pr`/`tr`.
**Severity** hard fail for `pr`/`tr`; warn for other views (cap 1 non-portable view).
**Means** the books load `panels/pr`. A missing link drops a symbol from the universe; a
broken link raises in the loader; an absolute target breaks the moment the store is read from
`/data/master` on Railway instead of the repo path.

### D-08 — no macOS sidecar or metadata files anywhere under the store
**Checks** no `._*` AppleDouble sidecars (hard) and no other junk such as `.DS_Store` (warn).
**Method** `os.walk` over the whole store.
**Pass** zero `._*`; junk count under cap 6.
**Severity** hard fail for `._*`; warn for the rest.
**Means** a `._X.csv` next to `X.csv` breaks every glob-based reader — this is exactly the bug
that killed the first Railway `mm_v1` run (`views.remove_junk_files`). `.DS_Store` files are
harmless to the `*.csv` globs but they ride along into archives and are the same class of
defect, so they are surfaced without failing the suite.

## B — calendar

### D-09 — the store's session calendar is the NSE calendar
**Checks** the union of session dates across every `adjusted_pr` file equals the set of
session dates in `bhavcopy_eq.parquet` restricted to the store's span, **and** no symbol
carries a date outside that set.
**Method** union of per-file date arrays from the fixture; parquet `date` column normalised.
Both set differences must be empty. (Note: `qa/calendar.csv` is *not* the calendar — it is the
store's own per-file defect list, see D-12. The parquet is the calendar of record, which is
what `qa_report.py` itself uses.)
**Pass** both differences empty.
**Severity** hard fail.
**Means** the books' calendar is the panel index. A session present for some symbols and
absent from the calendar becomes an all-NaN row after the pivot; a session missing everywhere
silently shortens every lookback window.

### D-10 — weekend sessions exist only where the calendar says so
**Checks** the Saturday/Sunday sessions in the store (muhurat and special sessions) are
exactly those in the parquet calendar.
**Method** filter both date sets to `dayofweek >= 5` and compare; report the list.
**Pass** sets identical (25 such sessions on the 2026-09-12 store).
**Severity** hard fail.
**Means** a fabricated weekend row would shift every monthly first-trading-day signal date
after it; a missing muhurat session drops a real trading day out of the book's calendar.

### D-11 — the store's own calendar defect list is empty
**Checks** `qa/calendar.csv` has zero rows (it lists files with non-midnight, duplicate or
off-calendar dates).
**Method** read and count.
**Pass** zero rows.
**Severity** hard fail.
**Means** the store's own QA pass has already found what D-02/D-09 assert; a non-empty file
with a green D-02 means the QA output is stale rather than clean.

## C — adjustment consistency

### D-12 — the adjusted view reproduces raw close x factor
**Checks** for every symbol and every session: `adjusted_pr.close == round(bhavcopy.close *
factor, 4)`, and the two files share an identical date index.
**Method** in the fixture, read `prices/bhavcopy/<SYM>.csv` alongside; compare with tolerance
`1.01e-4` — one 4-dp tick, because the store rounds with pandas' half-to-even on the binary
value and any re-derivation ties differently (282 symbols show exactly-1e-4 differences from
this alone; nothing larger).
**Pass** zero symbol-days beyond one tick; zero date-index mismatches.
**Severity** hard fail.
**Means** this is the audit trail of the whole adjusted layer, and the local half of
fortnightly check 1. If it breaks, the price the book scored on cannot be traced to the price
that traded, and the 15-day adjusted-band defect of 2026-09-11 (`project_om25_published_numbers_drift`)
is back.

### D-13 — the factor is piecewise constant and steps only on filed ex-dates
**Checks** `factor` changes only between two sessions that bracket a `corporate_actions.csv`
ex-date for that symbol or for one of the tickers it traded under.
**Method** step indices from `np.diff(factor)`; for each, require a CA ex-date in
`(date[i-1] - 4d, date[i] + 4d]`, matching on the symbol plus every alias in the bhavcopy
manifest's `traded_as`.
**Pass** zero unexplained steps.
**Severity** hard fail.
**Means** a factor step with no filing behind it is an adjustment nobody can justify — the
series was rewritten by something other than the CA table.

### D-14 — every share event for a current member in the book era is applied
**Checks** every `bonus` / `split` / `consolidation` row in `corporate_actions.csv` whose
ex-date falls inside a symbol's series span produces a factor step within +-5 days — asserted
for current Nifty 250 members with ex-date `>= 2014-01-01`.
**Method** compare the CA rows in span (deduped on `ex_date, type`, factor != 1) against the
factor-step dates.
**Pass** zero unapplied events in scope.
**Severity** hard fail.
**Means** an unapplied split leaves a 50-90% phantom one-day loss in the series. The
momentum score over the next 252 sessions is then wrong for that name in both direction and
size, and the inverse-vol weight computed from it is wrong too.

### D-15 — the same check over the whole store, as a count
**Checks** the population version of D-14: all symbols, all history.
**Method** as D-14 without the scope filter; warning carries the count, the split by whether
the CA row is an `observed:` (Kite/bhavcopy-derived) row or an NSE filing, and the first names.
**Pass** count under cap 700 (576 today).
**Severity** warn.
**Means** sizes the repair job and tells the founder whether the gap is systematic (one class
of CA row never applied) or scattered.

### D-16 — no unexplained one-day move beyond 50% in the adjusted view
**Checks** single-session moves `|ret| > 50%` in `adjusted_pr` that no CA ex-date within
6 days and no `qa/bad_prints.csv` row explains.
**Method** per-file `close` ratio; carve out CA-adjacent dates, `bad_prints` rows, and a small
reviewed allowlist of genuine market events named in the test file. Hard for current members
in the book era; warn globally.
**Pass** zero in scope; global count under cap 200 (116 today).
**Severity** hard fail (scoped) + warn (global).
**Means** the test cannot tell a genuine crash from an unadjusted corporate action, so it
produces a triage list and the cleared entries become an audited allowlist constant. An
uncleared entry is a missing CA filing: the book sees a fake collapse, drops the name, and
carries a wrong 252-day return for a year after it.

### D-17 — the total-return view never sits above the price-return view
**Checks** `adjusted_tr.factor <= adjusted_pr.factor` on every row where both exist, and the
two views cover the same symbols and the same date index per symbol.
**Method** per symbol, compare the factor columns and the indices.
**Pass** zero violations. (The brief's phrasing had this the other way round: back-adjustment
scales *history down*, and TR adds dividend factors on top of the PR ones, so the TR factor
and therefore the TR close is the **lower** of the two. Verified across the store.)
**Severity** hard fail.
**Means** if TR ever exceeds PR, dividends are being applied with the wrong sign, and the
Kite cross-check in group G (which runs against the dividend-inclusive basis) is meaningless.

### D-18 — every demerger was considered by the adjustment pass
**Checks** every `demerger` row in the CA table whose ex-date is inside a symbol's span
appears in `qa/adjustment_log.csv` as `measured` or `ignored:<5%`.
**Method** join the CA demerger rows in span against the log on `symbol, ex_date`.
**Pass** zero demergers absent from the log.
**Severity** hard fail.
**Means** the demerger factor is *measured* from the raw ex/cum close ratio rather than filed,
so the log is the only record that a decision was taken. A demerger missing from the log was
never seen, and the series carries the full split-off drop as a price loss.

### D-19 — no rights issue is left unadjusted for a current member in the book era
**Checks** `qa/adjustment_log.csv` notes that mean "the event was skipped":
`rights:no-price`, `rights:unparsed`, `dividend:unparsed-or-implausible`.
**Method** filter the log; hard for `rights*` notes on current members with ex-date in the
era; count the rest.
**Pass** zero rights skips in scope; global skip count under cap 80 (51 today).
**Severity** hard fail (scoped) + warn (global).
**Means** a rights issue with no issue price is applied as factor 1.0, i.e. not at all, so the
ex-date drop stays in the series as a fake loss. `dividend:unparsed` is harmless in the
price-return view by construction, which is why only the rights notes are hard.

## D — membership

### D-20 — the membership files load through the production loader
**Checks** all four `membership/*.csv` pass `scripts.universe_membership.load_membership`:
required columns present, every `effective_from` parseable and non-null, `effective_to`
strictly greater than `effective_from` where closed.
**Method** call the loader; a raise is the failure.
**Pass** all four load.
**Severity** hard fail.
**Means** the book runner calls `resolve_universe` on this file; a schema break stops the run.

### D-21 — no symbol holds two overlapping membership windows
**Checks** per file, per symbol, sorted windows do not overlap (open-ended treated as far
future).
**Method** `effective_from[1:] < effective_to[:-1]` per symbol group.
**Pass** zero overlapping symbols in all four files.
**Severity** hard fail.
**Means** an overlap double-counts a name in `members_asof`, so the member count is wrong and
the "exactly 250" invariant becomes untestable.

### D-22 — the Nifty 250 holds exactly 250 members on every recent session
**Checks** `members_asof` == 250 on every one of the last 250 sessions.
**Method** vectorised interval containment over the store calendar.
**Pass** exactly 250 on all 250 sessions.
**Severity** hard fail.
**Means** this is the universe the books rank. A 251st member is an extra candidate that the
published track never had; a 249th silently removes one.

### D-23 — index member counts never drift far from target over full history
**Checks** the same count since 2006-01-02 for `nifty250` (250), `nse500` (500),
`nifty100` (100), `nifty50` (50): the deviation from target never exceeds a per-index band, and
the number of off-target sessions is reported per year. Local half of fortnightly check 7.
**Method** as D-22 over the full calendar; warning carries per-year off-target session counts.
**Pass** max deviation inside the band — `nifty250` 5 (measured worst 4, in 2012), `nse500` 8
(measured worst 7, in 2006), `nifty100` and `nifty50` 2 (measured worst 1); and under 12,000
off-target sessions in total (9,168 today).
**Severity** warn.
**Means** the reconstruction's historical spells are not exact to the day — adds and drops at
a reconstitution carry slightly different effective dates, and second-line listings (the
`TATAMTRDVR` spell that makes the count 251 until 2024-08-30) were counted as separate
members. It biases any full-history backtest slightly, and it is the reason D-22 is scoped to
the recent window where the file is exact.

### D-24 — every member has a price file, and it covers the membership window
**Checks** each membership symbol has `prices/adjusted_pr/<SYM>.csv`, and the file's span
covers the part of the member's window that falls inside the store's span.
**Method** existence check plus first/last date comparison from the fixture summary.
**Pass** zero missing files and zero uncovered windows for `nifty250`; counts under cap 60 for
the other three indices.
**Severity** hard fail for `nifty250`; warn for the rest.
**Means** a member with no price file, or a file that starts years after the membership window
does, cannot be ranked — the universe was quietly short of 250 names for that spell. In
`nse500` it means the legacy universe references names the store never fetched.

### D-25 — effective dates and renames are coherent
**Checks** (a) `effective_from` / `effective_to` fall on trading days, counted and reported;
(b) for every rename in `symbol_changes.csv` where both the old and the new ticker carry
membership windows, those windows never overlap.
**Method** set membership against the store calendar; pairwise window overlap on rename pairs.
**Pass** zero overlapping rename pairs (hard); non-session effective dates under cap 320
(299 today — pre-2006 reconstruction spells, all on Sundays, plus the staged 2026-09-30
reconstitution).
**Severity** hard fail for the rename overlap; warn for the non-session dates.
**Means** a rename counted as two members double-counts the company on both sides of the
handoff — the single most likely cause of an off-by-one member count and of a book holding the
same company twice.

## E — benchmarks

### D-26 — every benchmark series has a usable schema
**Checks** each `benchmarks/*.csv`: a `date` column plus `close`, dates unique and strictly
increasing, `close` finite and `> 0`.
**Method** read each file; assert on the three conditions.
**Pass** all files clean.
**Severity** hard fail.
**Means** `load_benchmark` ffills the close; a NaN or a zero propagates into the regime ROC
and flips the book's bull/bear state.

### D-27 — the `_bench` variants agree with their base series
**Checks** for each `<IDX>` with both files, `<IDX>_bench.csv` has the same date index as
`<IDX>.csv` and an identical `close`.
**Method** inner join; max absolute difference must be 0; indices must be equal.
**Pass** exact agreement for all four pairs.
**Severity** hard fail.
**Means** the books read `NIFTY_100.csv` for the regime and `NIFTY_100_bench.csv` for the
equity comparison. If the two disagree, the regime and the benchmark tell different stories
about the same index.

### D-28 — the regime index is complete and current
**Checks** `NIFTY_100.csv` has a row for every store session inside its own span, and its last
date equals the store's latest session.
**Method** set difference against the store calendar; compare last dates.
**Pass** zero missing sessions, last dates equal.
**Severity** hard fail.
**Means** a gap in the regime index makes `roc_regime` compare closes 31 *rows* apart that are
not 31 *sessions* apart, so the bull/bear flip lands on the wrong day; a stale tail freezes the
regime at its last known state.

### D-29 — the other benchmark series have no session gaps
**Checks** the same gap test for every other benchmark file. Local half of fortnightly
check 10 (which compares levels against NSE's published values over the network).
**Method** as D-28, reported as counts per file.
**Pass** total gaps under cap 10 (6 today: `NIFTY_500` missing 2020-01-07,
`NIFTY_MIDCAP_150` missing 2008-12-31, legacy lowercase `nifty100.csv` missing 4 and stale
since 2026-08-21).
**Severity** warn.
**Means** these series are not on the books' path; the legacy lowercase `nifty100.csv` is a
leftover and should be deleted rather than repaired, but a growing gap count on
`NIFTY_500`/`NIFTY_MIDCAP_150` would mean the index fetch is dropping days.

## F — book-facing readiness

### D-30 — the panel loader loads the store the books read
**Checks** `ensure_panel_views` then `load_price_panels(master/"panels/pr")` runs without
error; the resulting index equals the store session calendar; the last date equals the store's
latest session; no column is entirely NaN; the trade panel has the same shape.
**Method** call the production functions directly.
**Pass** all four conditions.
**Severity** hard fail.
**Means** this is the exact call `build_and_run` makes. If it fails, neither book runs.

### D-31 — every current member has enough history or is a recent entrant
**Checks** each current Nifty 250 member has `>= 220` observed closes (the stricter of the two
books' `min_obs`) **or** its first session is inside the last 300 sessions.
**Method** count non-NaN closes per member from the loaded panel.
**Pass** every member satisfies one of the two.
**Severity** hard fail. The recent-entrant list is always reported.
**Means** a member with a short history and an old listing date means the price file is
truncated. Legitimate recent entrants (4 today: `GROWW` 206, `ICICIAMC` 179, `LENSKART` 208,
`TMCV` 206, all listed Nov-Dec 2025) are simply not yet scoreable, which is the intended
behaviour of `min_obs`, not a data fault.

### D-32 — every current member has a sector label
**Checks** `load_sector_map()` returns a label for every current Nifty 250 member, and every
label is one of the 21 NSE macro sectors.
**Method** call `data_pipeline.strategies.sectors.load_sector_map`; set difference. Local half
of fortnightly check 11.
**Pass** zero unlabelled members; label vocabulary size 21.
**Severity** hard fail.
**Means** the engine's `sector_cap=5` treats an unlabelled name as unconstrained, so one
missing label quietly lifts the cap for that name — the wrong default for a live book.

### D-33 — the regime series computes over the full calendar
**Checks** `roc_regime(NIFTY_100.csv, 31, 3, calendar)` returns a boolean series covering the
whole calendar with no NaN after the documented warm-up, and both states occur.
**Method** call the production function with the book's locked parameters.
**Pass** length equals the calendar, zero NaN, both `True` and `False` present.
**Severity** hard fail.
**Means** an all-`True` regime means the bear branch of both books has silently never fired;
NaNs mean `fillna(True)` is masking a broken index series.

### D-34 — no current member's price series is stale
**Checks** each current member's last session equals the store's latest session, unless the
symbol is listed in `qa/stale_tails.csv`.
**Method** per-member last date from the fixture summary.
**Pass** zero unlisted stale members (0 today).
**Severity** hard fail.
**Means** the loader ffills, so a stale member silently holds yesterday's price at today's
rebalance — the book would size and trade a stale quote.

### D-35 — the store's latest session is recent
**Checks** the store's latest session is within 3 weekdays of today.
**Method** `pd.bdate_range` between the latest session and today.
**Pass** gap under cap 3 weekdays.
**Severity** warn.
**Means** a book run today is only as current as the store. Today the store ends 2026-09-09
with 2 weekdays outstanding — the bhavcopy/Kite refresh has not landed 09-10 and 09-11 locally
even though `qa/nightly_latest.json` is dated 2026-09-11.

## G — Kite cross-check, offline

### D-36 — the price-return view against Kite: step census
**Checks** for the 1,041 symbols with a Kite file, the ratio `adjusted_pr.close /
kite.close` is piecewise constant; count the steps beyond 0.4%.
**Method** the `verify_kite_adjustment` idea applied to the adjusted view instead of the raw
one: 5-day median before vs after each day, flag `|step - 1| > 0.4%`, collapse runs. Local
offline half of fortnightly checks 1 and 2.
**Pass** step count under cap 25,000 (18,102 today over 382 symbols).
**Severity** warn.
**Means** this pair is *expected* to step: Kite's series is dividend-adjusted and the
price-return view is not, so every meaningful dividend is a step. The census is a baseline —
a jump in it means either the store's adjustment or Kite's changed wholesale.

### D-37 — large share-scale disagreements with Kite
**Checks** steps beyond 10% in the same ratio — too large to be an ordinary dividend — that no
dividend row in the CA table within 8 days explains (a dividend explains a step when
`amount / p_cum` is within 3 pp of the step size). Reported for current Nifty 250 members with
step dates in the book era, and as a global count.
**Method** as D-36 at a 10% threshold, plus the dividend carve-out.
**Pass** global count under cap 400 (279 today, over 313 raw steps before the dividend
carve-out); the in-scope list (10 today) is carried in the warning and must be triaged in
RESULTS.md.
**Severity** warn (the hard, holdings-scoped version is D-38).
**Means** a step this large is a corporate action one of the two sides did not apply, or applied
with a different factor. The in-scope list separates into two classes: unapplied `observed:`
splits (the D-14 failures) and demergers where the store's *measured* ex/cum ratio differs from
Kite's factor.

### D-38 — held names reconcile against Kite — SKIPPED
**Checks** the same test as D-37 restricted to the names `mm_v1` and `om25_v4` currently hold,
as a hard failure.
**Method** read the holdings from the latest runner output under
`data/<book>_portfolios/latest.json`.
**Pass** zero unexplained steps for a held name.
**Severity** hard fail when enabled — **skipped** today: no runner output exists locally for
either book, so there are no holdings to read. Un-skips automatically once
`scripts/run_rebuilt_book.py` has been run locally. The live-Kite version of this check is
fortnightly check 1 and stays out of this suite by design (network).

## H — manifests and QA files

### D-39 — every price file on disk is in its manifest, with a matching sha256
**Checks** for `bhavcopy` and `kite`: every file on disk has a manifest entry, and its sha256
and row count match the entry. Local half of fortnightly check 13.
**Method** hash all 3,560 files (776 MB, ~1 s with the page cache warm) and compare.
**Pass** zero files absent from the manifest, zero hash or row-count mismatches.
**Severity** hard fail.
**Means** a mismatch means a price file was edited outside the pipeline — the case check 13
exists for, and the one that would let a hand-patched series into a published track.

### D-40 — no manifest entry points at a file that does not exist
**Checks** the reverse direction of D-39.
**Method** set difference; hard if a current Nifty 250 member is involved.
**Pass** zero current members affected; total orphan entries under cap 60 (55 today: 14 in
`bhavcopy`, 41 in `gdf`, none flagged `delisted_on`).
**Severity** hard fail (scoped) + warn (global).
**Means** the manifest is the store's inventory. An entry with no file means the export dropped
a symbol, or the file was deleted — `nse500` membership still references all 14 of the
`bhavcopy` orphans.

### D-41 — the QA files parse with the schema the gate expects
**Checks** `qa/bad_prints.csv`, `qa/stale_tails.csv`, `qa/calendar.csv`,
`qa/kite_steps_unexplained.csv`, `qa/adjustment_log.csv`, `qa/observed_events.csv` and
`corporate_actions.csv` all read and carry their expected columns; CA share-event factors are
finite and `> 0`; no `(symbol, ex_date, type)` appears twice with conflicting factors.
**Method** read each; compare column sets; group the CA table.
**Pass** all files present and well-formed; conflicting-duplicate count under cap 50.
**Severity** hard fail for the schemas; warn for conflicting duplicates.
**Means** `scripts/refresh_master_store.py::qa_gate` summarises these files into
`nightly_latest.json`; a renamed column makes the gate report "ok" because it found nothing to
count.

### D-42 — the nightly gate output is fresh and self-consistent
**Checks** `qa/nightly_latest.json` parses, carries `date`, `status`, `bad_prints_30d`,
`stale_tails`, `calendar_issues`, `kite_steps_unexplained_30d`; `status` is `ok` or `flagged`;
its `stale_tails` and `calendar_issues` match the row counts of the CSVs they summarise; and
its date is within 4 calendar days of today. Local half of fortnightly check 12.
**Method** read the JSON and the two CSVs; compare.
**Pass** parses with all keys and a valid status (hard); counters agree and the date is recent
(warn).
**Severity** hard fail on parse/shape; warn on staleness and counter drift.
**Means** the gate is the only automatic statement that the nightly ran. `flagged` on a
standing list is accepted (about 30 unexplained Kite steps in 30 days); a *missing* or stale
file means the morning review has been running blind.
