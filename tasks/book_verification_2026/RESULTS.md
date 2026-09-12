# RESULTS — book verification 2026

## Data suite — first run 2026-09-12

Store under test: `data/master` on branch `index_reconstruction`, latest session **2026-09-09**,
2,519 symbols in `prices/adjusted_pr`, 1,041 with a Kite series, calendar 2005-01-03 → 2026-09-09
(5,380 sessions). Test list: `TESTS_DATA.md` (D-01..D-42). Nothing in the store or in
`data_pipeline/` was changed to make a test pass.

```
.venv/bin/python -m pytest tasks/book_verification_2026/tests/test_data_*.py \
    -p no:cacheprovider -W "default::UserWarning" -rw -q
```

**42 tests — 23 pass clean, 14 pass with a reported warning, 4 fail, 1 skipped. 44 s.**

### Verdicts

| ID | Test | Verdict | Note |
|---|---|---|---|
| D-01 | adjusted_pr parses with the expected schema | PASS | 2,519 files, 8,001,134 rows |
| D-02 | dates midnight, unique, strictly increasing | PASS | zero defects |
| D-03 | closes finite and positive | PASS | |
| D-04 | OHLC bars internally consistent | PASS | with the 4-dp rounding tolerance |
| D-05 | volumes finite and non-negative | PASS | |
| D-06 | factor usable, last row exactly 1.0 | PASS | all 2,519 |
| D-07 | panel views mirror source, links portable | WARN | `pr`/`tr` clean; `panels/pr_full` uses absolute targets |
| D-08 | no macOS sidecars or metadata files | WARN | 0 `._*`; 3 `.DS_Store` (store root, `prices/`, `panels/`) |
| D-09 | store sessions are the NSE calendar | PASS | 5,380 = 5,380, both differences empty |
| D-10 | weekend sessions only where the calendar has them | PASS | 25 special sessions, identical sets |
| D-11 | `qa/calendar.csv` defect list empty | PASS | 0 rows |
| D-12 | adjusted close = raw close x factor | PASS | 0 rows beyond one 4-dp tick |
| D-13 | factor steps only on filed ex-dates | PASS | 1,732 steps, 0 unexplained |
| D-14 | share events applied for current members in era | **FAIL** | 4 events, see below |
| D-15 | share-event application gap, whole store | WARN | 576 (572 `observed:*`, 4 NSE filings) |
| D-16 | unexplained one-day moves > 50% | **FAIL** | 2 in scope; 116 globally |
| D-17 | TR factor never above PR factor | PASS | direction in the brief was inverted, see below |
| D-18 | every demerger considered by the adjustment pass | PASS | 136 logged (116 measured, 20 ignored < 5%) |
| D-19 | no rights issue left unadjusted for a current member | **FAIL** | 2 in scope; 51 skips globally |
| D-20 | membership files load through the production loader | PASS | all four |
| D-21 | no overlapping membership windows per symbol | PASS | all four files |
| D-22 | Nifty 250 = exactly 250 on every recent session | PASS | last 250 sessions exact |
| D-23 | member counts within band over full history | WARN | 9,168 off-target sessions; worst deviation 4 (n250) / 7 (nse500) |
| D-24 | every member has a price file covering its window | **FAIL** | 4 Nifty 250 windows uncovered |
| D-25 | effective dates and renames coherent | WARN | 0 rename overlaps; 299 non-trading-day effective dates |
| D-26 | benchmark schemas usable | PASS | 9 files |
| D-27 | `_bench` variants agree with their base | PASS | 4 pairs, exact |
| D-28 | regime index complete and current | PASS | `NIFTY_100.csv` 0 gaps, ends 2026-09-09 |
| D-29 | other benchmark series have no session gaps | WARN | 8 gaps across 5 files |
| D-30 | panel loader loads the store the books read | PASS | (5380, 2519), index == calendar |
| D-31 | current members have history or are recent entrants | WARN | 4 recent entrants below `min_obs` |
| D-32 | current members all have a sector label | PASS | 250/250, 21 sectors |
| D-33 | regime computes over the full calendar | PASS | 0 NaN, 35.4% of sessions bear |
| D-34 | no current member's series is stale | PASS | all 250 end 2026-09-09 |
| D-35 | store latest session is recent | WARN | 2 weekdays outstanding |
| D-36 | PR view vs Kite, step census | WARN | 18,102 steps over 382 symbols (expected: dividends) |
| D-37 | large share-scale disagreements with Kite | WARN | 279; 10 on current members inside the era |
| D-38 | held names reconcile against Kite | SKIP | no local runner output for either book |
| D-39 | every price file in its manifest with a matching sha256 | PASS | 3,560 files, 776 MB, 0 mismatches |
| D-40 | no manifest entry points at a missing file | WARN | 55 orphans (14 `bhavcopy`, 41 `gdf`), none a current member |
| D-41 | QA files parse with the gate's schema | WARN | schemas clean; 17 conflicting CA duplicates |
| D-42 | nightly gate output fresh and self-consistent | PASS | `flagged`, 2026-09-11, counters agree |

### Failures

**D-14 — four corporate actions on current Nifty 250 members are not applied to the adjusted
view.** Store bug in `data_pipeline/master_store/build_adjusted.py`.

| Symbol | Ex-date | Event | Factor | Source of the CA row |
|---|---|---|---|---|
| CGPOWER | 2015-01-01 | split | 0.341263 | `observed:kite-observed` |
| CONCOR | 2015-01-01 | split | 0.800000 | `observed:kite-observed` |
| ADANIENT | 2015-06-03 | split | 0.296819 | `observed:kite-observed` |
| MFSL | 2016-01-27 | split | 0.473684 | `observed:kite-observed` |

Every one is an `observed:` row — an event `derive_observed_events.py` inferred from a step in
the Kite (or bhavcopy) series that NSE never filed. These rows carry no ISIN. `build_adjusted`
collects a symbol's events by the ISIN each identity window traded under and falls back to
symbol matching *only for windows with no known ISIN*; a name like ADANIENT has a known ISIN, so
its symbol-keyed observed rows are never picked up and the factor is never applied. The effect
is direct and large — ADANIENT's adjusted close goes 617.56 → 106.40 on 2015-06-03, an
unadjusted −83% day, while Kite's own series is continuous across it:

```
prices/adjusted_pr/ADANIENT.csv   2015-06-02  617.56    2015-06-03  106.40   factor 0.969485 throughout
prices/kite/ADANIENT.csv          2015-06-02  183.20    2015-06-03  106.40
```

A book scoring ADANIENT any time in the following 252 sessions reads a catastrophic loss that
never happened, and the 63-day vol it sizes on is wrong for three months. The same applies to
CGPOWER, CONCOR and MFSL. **Verdict: store bug, repair before either book is published from this
store.** The population of the same defect is 576 events over 164 symbols (D-15), 572 of them
`observed:` rows — including RELIANCE 2006-01-18, ITC 2005-09-21 (factor 0.0667), KOTAKBANK
2005-08-25 and TATASTEEL 2007-10-29. Those four sit before the books' data era, so they are
warnings rather than failures, but they make any research run that starts before 2014
unreliable.

**D-16 — two unexplained > 50% one-day moves on current members inside the book era.** Data
gap: a corporate action neither NSE's feed nor Kite ever recorded.

| Symbol | Date | Move | Diagnosis |
|---|---|---|---|
| JSL | 2015-11-19 | −60.9% | Jindal Stainless demerger. No CA row at all; Kite shows the same drop, so both sides are unadjusted. |
| CGPOWER | 2016-03-15 | −71.7% | CG Power restructuring. No CA row; Kite shows the same drop. |

Neither is in `qa/bad_prints.csv` (the price does not revert). Because both feeds agree, no
cross-check can find these — only this jump test can. **Verdict: data gap to repair — add the
two events to `corporate_actions.csv` with a measured factor, then re-run `build_adjusted`.**
Globally the test lists 116 such moves; two more on current members (YESBANK 2020-03-06 and
2020-03-17, the RBI moratorium and the rebound) are genuine market events and are carried in the
suite's `REVIEWED_GENUINE_MOVES` allowlist with that reason.

**D-19 — two rights issues on current members were applied as factor 1.0, i.e. not at all.**
Data gap: the filing has no issue price, so `event_factor` returns 1.0 and logs
`rights:no-price`.

| Symbol | Ex-date | Log note |
|---|---|---|
| CANBK | 2017-02-17 | `rights:no-price` |
| TATASTEEL | 2018-01-31 | `rights:no-price` |

The ex-date drop therefore remains in the series as a price loss. `qa/adjustment_log.csv` records
44 such rights skips and 7 `dividend:unparsed-or-implausible` skips in total; the dividend ones
are harmless in the price-return view by construction, which is why only the rights notes fail.
**Verdict: data gap to repair — the issue price has to come from the filing detail or NSE's
circular, per symbol.**

**D-24 — four Nifty 250 membership windows have no prices behind them.** Store bug in the
canonical-symbol mapping of `emit_pit_membership.py`.

| Symbol | Membership window | Price file covers | Membership note |
|---|---|---|---|
| GUJENERGY | 2016-04-01 → 2026-03-30 | 2019-01-16 → 2026-09-09 | Gujarat Gas Ltd. [survivor-rename] |
| HEXT | 2005-09-25 → 2008-03-14 | 2025-02-19 → 2026-09-09 | Hexaware Technologies Ltd. [current-list] |
| KIRLOSBROS | 2006-09-01 → 2009-10-22 | 2010-04-20 → 2026-09-09 | Kirloskar Brothers Ltd. [kite-dump] |
| ORCHPHARMA | 2005-09-25 → 2009-03-27 | 2020-11-03 → 2026-09-09 | Orchid Pharma Ltd. [kite-dump] |

A historical membership spell has been attached to the ticker the company trades under *now*
rather than the line it traded under *then*: HEXT's series starts at Hexaware's 2025 relisting,
ORCHPHARMA's at its 2020 relisting, and GUJENERGY's (Gujarat Gas, survivor-rename) three years
after the window opens. For those spells the ranked universe was silently short of 250 names —
which is also what the store's own coverage table shows as 98-100% rather than 100%. GUJENERGY is
the one inside the books' data era (2016-04 → 2019-01, about 700 sessions). **Verdict: store
bug — the membership row needs the same `LINE_OVERRIDES` split the reconstruction applies
elsewhere, or the symbol needs its pre-relisting history fetched.** The same test warns that
`nse500` references 14 members with no price file at all (13 delisted 1998-2007, plus BAGMANE
staged for the 2026-09-30 reconstitution); those 14 are also the `bhavcopy` manifest orphans of
D-40.

### Warnings worth the founder's attention

- **D-37 — 10 share-scale disagreements with Kite on current members inside the book era**, in
  two classes. The first is the D-14 bug seen from the other side (CGPOWER 2014-12-30 0.341,
  CONCOR 2014-12-30 0.800, ADANIENT 2015-06-01 0.297, MFSL 2016-01-22 0.476). The second is a
  **demerger convention difference**: TATACOMM 2019-09-13 (1.533), MOTHERSON 2022-01-12 (1.132),
  NMDC 2022-10-24 (0.539), SIEMENS 2025-04-03 (1.335), TMPV 2025-10-10 (1.150), VEDL 2026-04-28
  (1.491). All six *are* applied by the store (`qa/adjustment_log.csv` shows measured factors
  0.35-0.80), but the store measures the factor as the raw ex-day / cum-day close ratio, which
  includes that day's market move, while Kite uses the official entitlement ratio. Every one is a
  large, currently held-scale name. This is a methodology question for the founder, not a bug:
  the measured convention is documented in `build_adjusted.py`, but it means six current members
  carry a demerger factor that differs from Kite's by 13-53%.
- **D-23 — the point-in-time files are exact only recently.** `nifty250` is exactly 250 on every
  session of the last 250 and through 2025-26, but off target on 3,101 sessions since 2006 (worst
  deviation 4). The recurring cause is second-line listings counted as separate members — the
  `TATAMTRDVR` spell keeps the count at 251 until 2024-08-30 — and reconstitution adds and drops
  carrying different effective dates. `nse500` is worse (worst deviation 7, in 2006).
- **D-35 — the local store is two weekdays behind.** Latest session 2026-09-09 while
  `qa/nightly_latest.json` is dated 2026-09-11: the gate ran, the data did not land. Consistent
  with the known repo-root-live / mirror-lags topology, but it means a book run here today would
  rebalance on 09-09 prices.
- **D-08 / D-07 — housekeeping.** Three `.DS_Store` files in the store (no `._*` sidecars, so the
  loader is safe today) and `panels/pr_full` built with absolute symlink targets, which would
  break if that view were ever read from `/data/master`.
- **D-31 — four current members are not yet scoreable**: GROWW (206 sessions), ICICIAMC (179),
  LENSKART (208), TMCV (206), all listed Nov-Dec 2025. That is `min_obs` working as designed, but
  it means the books rank 246 of 250 names until about February 2027.

### Corrections to the brief, and one test recalibrated

- **D-17 direction.** The brief asked for `adjusted_tr >= adjusted_pr`. Back-adjustment scales
  *history down* and the TR view multiplies the PR factors by dividend factors, so the TR factor
  and the TR close are the **lower** of the two. The test asserts `tr_factor <= pr_factor`, which
  holds on every row of all 2,519 symbols.
- **`qa/calendar.csv` is not the NSE calendar.** The brief described it as the calendar to compare
  against; it is `qa_report.py`'s per-file *defect* list (currently empty, 0 rows). The calendar of
  record is the distinct date set of `bhavcopy_eq.parquet`, which is what `qa_report.py` itself
  uses and what D-09/D-10 compare against. D-11 asserts the defect list is empty.
- **D-38 skipped as the brief allows.** There is no `data/mm_v1_portfolios/` or
  `data/om25_v4_portfolios/` output locally, so there are no holdings to scope a hard Kite check
  to. The test un-skips as soon as `scripts/run_rebuilt_book.py` has been run here.
- **D-23 band widened once, before this run was recorded.** The first pass asserted a 5-member
  band for every index; `nse500` measures 7 in 2006. The band is now per index (250: 5, 500: 8,
  100/50: 2), calibrated to the measured worst case and documented in `TESTS_DATA.md`. That was a
  test miscalibration on my part, not a change in the store.

### What has to change before the next deploy

1. **`build_adjusted.py` must apply `observed:` corporate-action rows** (D-14, D-15). They are
   currently collected only for identity windows with no known ISIN, so 572 inferred events —
   including four on current Nifty 250 members inside the book era — are silently dropped. This
   is the single highest-impact item: it puts fake −50% to −85% days in the middle of the
   momentum lookback of names both books can hold.
2. **Add the two missing demerger filings** (JSL 2015-11-19, CGPOWER 2016-03-15) and the two
   rights issue prices (CANBK 2017-02-17, TATASTEEL 2018-01-31), then rebuild the adjusted views
   (D-16, D-19).
3. **Fix the four mis-attributed Nifty 250 membership spells** (GUJENERGY, HEXT, KIRLOSBROS,
   ORCHPHARMA) or fetch the pre-relisting history they point at (D-24).
4. **Founder call on the demerger factor convention** — measured ex/cum ratio versus the official
   entitlement ratio — which currently puts six current members 13-53% away from Kite (D-37).
5. **Refresh the local store** so its latest session is today's, and clear the three `.DS_Store`
   files with `views.remove_junk_files` before any archive is built (D-35, D-08).

---

## Books suite — first run 2026-09-12

Books under test: `mm_v1` and `om25_v4`, run fresh from **2010-01-01** through
`scripts/run_rebuilt_book.py` against `data/master` on branch `index_reconstruction` (calendar
2005-01-03 → 2026-09-09, 598 Nifty 250 members ever, price-return panel view). Test list:
`TESTS_BOOKS.md` (B-A-01 .. B-H-08, written there as A-01 .. H-08). Nothing in
`scripts/_clean_engine.py`, `scripts/rebuilt_books.py` or `data_pipeline/strategies/` was changed to
make a test pass.

```
.venv/bin/python -m pytest -q tasks/book_verification_2026/tests/test_books_*.py -p no:cacheprovider
```

(`pytest -q tasks/book_verification_2026/tests` runs both suites, 144 tests.
`BOOK_VERIFY_RUNS=<dir>` reuses an earlier pair of runs instead of re-running the books.)

**54 test functions, 102 parametrised instances — 98 pass, 4 fail. 50 s** (26 s of that is the two
book runs, 10 s the price-panel load, 5 s the replay).

The run itself reproduces the §23 decision-line figures exactly:

| Book | CAGR 2010-26 | Max DD | Sharpe | Trades | Reference (§23, k=1) |
|---|---|---|---|---|---|
| `mm_v1` | 23.5% | −26.3% | 1.15 | 1,873 | 23.5% / −26.3% |
| `om25_v4` | 22.6% | −28.3% | 1.20 | 1,681 | 22.6% / −28.3% |

### Verdicts

| ID | Test | mm_v1 | om25_v4 |
|---|---|---|---|
| A-01 | entrants come from the top 45 by rank | PASS | PASS |
| A-02 | entrants are members as of the signal date | PASS | PASS |
| A-02b | score never sees a future index addition | PASS | PASS |
| A-03 | entrants meet min_obs (219 / 220) | PASS | PASS |
| A-04 | score window ends 21 sessions before the signal | PASS | PASS |
| A-05 | MM score = vol-adj momentum, 5% vol floor | PASS | n/a |
| A-05b | no entrant relies on the vol floor | PASS | PASS |
| A-06 | OM25 score = 50/50 rank blend | n/a | PASS |
| A-07 | return filter on the blend, not on MM | PASS (one test, both books) | |
| A-08 | entrants are priced, not forward-filled | PASS | PASS |
| A-09 | signals file reproduces the ranking | PASS | **FAIL** |
| B-01 | signal dates = first trading day of each month | PASS | PASS |
| B-02 | trades execute on the next session only | PASS | PASS |
| B-03 | one action day a month, exits and entries together | PASS | PASS |
| B-04 | no weekly / trim / regime machinery active | PASS | PASS |
| C-01 | exit reasons and one SELL per exit | PASS | PASS |
| C-02 | rank exits are the holdings below the buffer | PASS | PASS |
| C-03 | stop exits are the 20% breaches at the signal close | PASS | PASS |
| C-04 | peak is the running peak of closes since entry | **FAIL** | PASS |
| C-05 | the stop never fires between signal dates | PASS | PASS |
| C-06 | stop exits fill next session at the trade panel | PASS | PASS |
| C-07 | a stopped name is never rebought the same day | PASS | PASS |
| C-08 | the re-entry block lasts exactly one entry date | PASS | PASS |
| D-01 | entrants and share counts reproduce exactly | PASS | PASS |
| D-02 | no entry weight above 10% | PASS | PASS |
| D-03 | entry weights are inverse-volatility | PASS | PASS |
| D-04 | sizing uses no data after the signal date | PASS | PASS |
| D-05 | cash never negative, small in a full bull book | PASS | PASS |
| D-06 | equity = cash + marked holdings, every day | PASS | PASS |
| D-07 | no partial sells, no trims | PASS | PASS |
| D-08 | no held position is topped up | PASS | PASS |
| D-09 | costs, fill prices, starting capital | PASS | PASS |
| E-01 | at most 5 names per labelled sector | PASS | PASS |
| E-02 | the cap skips lower-ranked entrants | PASS | PASS |
| E-03 | unlabelled names unconstrained (synthetic) | PASS (one test) | |
| E-03b | the map is NSE's 21-sector scheme, >=95% coverage | PASS (one test) | |
| F-01 | regime = NIFTY 100 ROC31, 3-day confirm, lagged | PASS | PASS |
| F-02 | bull books hold at most 25 | PASS | PASS |
| F-03 | bear entries capped at 15 | PASS | PASS |
| F-04 | bear exit rank is 35 | PASS | PASS |
| F-05 | a bear runs the book down only as positions exit | PASS | PASS |
| F-06 | bear entrants keep full inverse-vol size | PASS | PASS |
| G-01 | score at t ignores data after t | PASS | PASS |
| G-03 | regime at t ignores data after t | PASS | PASS |
| G-04 | prices after an exec date cannot change earlier trades | PASS (synthetic) | |
| G-05 | no stop decision depends on the exec-day close | PASS | PASS |
| H-01 | metrics.json carries the LOCKED config | PASS | PASS |
| H-02 | metrics.json tail matches the run | PASS | PASS |
| H-03 | DB-facing trades reconcile | PASS | PASS |
| H-04 | DB-facing equity reconciles | PASS | PASS |
| H-05 | DB-facing holdings reconcile | PASS | PASS |
| H-06 | DB-facing metrics reconcile | PASS | PASS |
| H-07 | run reproduces the §23 reference figures | PASS | PASS |
| H-08 | per-trade P&L is net of both slippage legs | **FAIL** | **FAIL** |

G-02 of the list is the sizing leg of the same truncation invariant and is implemented as D-04.

### The four failures

#### 1. A-09 — the published signals file is not the buy list the engine used (`om25_v4`)

**Bug in the assembly, dashboard-facing, not a rule question.**

`scripts/rebuilt_books.py:77` builds `<book>_signals.csv` with
`sc.sort_values(ascending=False).head(top_n + exit_buffer)`. The engine builds its own ranking with
`scores.nlargest(top_n + exit_buffer)` (`scripts/_clean_engine.py:270`). The two order *ties*
differently, and OM25 v4's score is a percentile-rank blend, so ties at the 45th place are common:
the order differs on **122 of 201** signal dates and the *set* of 45 names differs on **9**. The
engine's own ranking is the one that traded, so no trade is wrong — D-01, A-01 and C-02 all
reconcile exactly against `nlargest` — but the file the dashboard reads shows a different buy list.
Two of the nine are material and recent:

| Signal date | Shown in the signals file | Actually in the engine's 45 | What traded |
|---|---|---|---|
| 2025-11-03 | CREDITACC | ASHOKLEY | ASHOKLEY bought; it is absent from the signals file |
| 2026-01-01 | GODFRYPHLP | GLENMARK | GLENMARK bought; GODFRYPHLP stopped out |

The other seven (2014-08-01 IIFL/VTL, 2017-04-03 RECLTD/TRENT, 2018-02-01 ABIRLANUVO/RADICO,
2018-08-01 CYIENT/SYNGENE, 2019-01-01 GRUH/HONAUT, 2019-06-03 GFLLIMITED/HCLTECH, 2026-07-01
GMDCLTD/NAM-INDIA) sit at rank 45 and never traded. `mm_v1` is unaffected — its score is a
continuous ratio, so ties are effectively absent.

**Fix**: one line — build the signals rows from the same `nlargest` call the engine uses, e.g.
`sc.nlargest(cfg["top_n"] + cfg["exit_buffer"])` with the same ordering the engine derives, at
`scripts/rebuilt_books.py:77`. Zero effect on trades, equity or metrics; it changes only the
published rank view. Better still, have `build_and_run` return the ranking the engine precomputed
rather than re-deriving it, so the two cannot drift again.

#### 2. C-04 — the peak excludes the entry session's own close (`mm_v1`)

**Rule question for the founder, with a one-line engine nuance behind it.**

`run_strategy` updates each position's trailing peak at the top of the daily loop
(`scripts/_clean_engine.py:341-349`), *before* the entry block sets `entry_meta[sym] = {'peak':
exec_price}` (`:767`, `:806`). A name bought on session E therefore has `peak = entry trade price`
for the rest of E; the entry session's close is folded in only on E+1. So the engine's peak is
`max(entry trade price, closes from the session after entry)`, not "the running peak of closes since
entry". The engine's own comment at `:341-343` says "all closes from entry to today inclusive",
which is not what the code does.

This changes exactly one decision in sixteen years of `mm_v1` and none in `om25_v4`:

| | LTTS |
|---|---|
| Entered | 2022-01-04 at 5,817.33 (trade price) |
| Entry-session close | 5,916.30 |
| Next close | 5,842.60 |
| Engine peak | 5,842.60 |
| Literal peak | 5,916.30 |
| Signal close 2022-02-01 | 4,694.50 |
| Engine drawdown from peak | −19.65% → no stop |
| Literal drawdown from peak | −20.65% → stop |

The position left anyway that day on a rank exit, so the trade log is the same; only the exit
*reason* differs. Nothing is materially wrong, but the spec and the code disagree.

**Decision needed**: either (a) MECHANICS is amended to say the peak runs from the entry trade price
and the following session's close — the engine stays byte-identical and the locked figures stand; or
(b) the engine folds the entry-session close in (move the peak seed to
`max(exec_price, close[entry_date])` at `:767`/`:806`), which is one line but re-prices the locked
record and needs a fresh §23-style comparison. Recommendation: (a). The information content is
trivial and option (b) invalidates the reference figures for a one-in-two-hundred exit-reason label.

#### 3, 4. H-08 — `exits.pnl_pct` is gross of the sell-side slippage leg (both books)

**Bug, and it contradicts a standing founder instruction; it is not a rule question.**

All four exit paths compute `pnl_pct = exec_price / avg_cost - 1`
(`scripts/_clean_engine.py:411`, `:549`, `:598`, `:645`). `avg_cost` is `cost_basis / shares` and
`cost_basis` was accumulated as `shares * price * (1 + slippage)`, so the **buy** leg is net of
slippage while the **sell** leg is gross. Every exit's reported P&L is therefore overstated by
20 bp, and `hit_rate_overall` in `metrics.json` and `momentum_metrics.csv` inherits it (it is
`(pnl_pct > 0).mean()`, so exits between 0 and +20 bp are counted as winners when they are not).
Measured over both books: the test's net reconstruction differs from the recorded `pnl_pct` on all
912 (`mm_v1`) and 818 (`om25_v4`) exit rows, and the recorded values match the gross form exactly.

Equity, CAGR, Sharpe and drawdown are **not** affected — the cash accounting applies both legs
correctly (`cash += sh * exec_price * (1 - slippage)` on every sell), which D-06 confirms to the
rupee. Only the per-trade figures and the hit rate are wrong.

**Fix**: `pnl_pct = exec_price * (1 - slippage) / avg_cost - 1` at all four sites. This is the same
correction the founder already made once (`feedback_pnl_net_of_slippage`). It changes the published
hit rate slightly downward for every book that runs through `run_strategy`, including the four
legacy production books, so it wants one deliberate commit and a DB re-sync rather than a quiet edit.

### What must change before the next deploy

1. **Fix A-09** (`scripts/rebuilt_books.py:77`) — the rebalance view can name the wrong stock.
   Trades are unaffected, so this is safe to ship on its own.
2. **Fix H-08** (`scripts/_clean_engine.py:411/549/598/645`) — per-trade P&L and hit rate. Affects
   every book, so re-sync all seven after the fix and re-run this suite.
3. **Founder call on C-04** — amend MECHANICS to the engine's peak convention (recommended) or
   change the engine and re-baseline. Blocking only in the sense that the spec and the code should
   not disagree in writing.
4. Nothing in selection, timing, sizing, cash, the sector cap, the regime or the look-ahead guards
   needs to change: A-01..A-08, B, C-01..C-03, C-05..C-08, D, E, F and G all pass on both books, and
   H-07 shows the run still reproduces the §23 figures to the basis point.

---

## Store repair and re-baseline 2026-09-12

The four data-suite failures are repaired and both books re-run. Full detail, sources and the
unresolved residue are in `REPAIRS.md`; this section is the scoreboard. Local only; nothing
deployed, no LOCKED config or rule touched.

### Suite counts, before and after

| Suite | Before | After |
|---|---|---|
| Data (D-01..D-42) | 23 pass clean, 14 pass with a warning, **4 fail**, 1 skip | **41 pass (14 with a warning), 0 fail, 1 skip** |
| Books (102 instances) | 98 pass, 4 fail (A-09, C-04, H-08 x2) | **101 pass, 1 fail (C-04)** |

A-09 and H-08 were fixed in commit `f136d2c` before this work; the only book test still red is
**C-04**, the open founder question about the trailing-stop peak convention. No data test was
recalibrated — every failure was repaired in the store or its pipeline, not in the assertion.

| ID | Before | After | What moved |
|---|---|---|---|
| D-14 | **FAIL** (4 events) | PASS | collection bug fixed; two of the four were Kite artefacts, two were mis-typed demergers |
| D-15 | WARN 576 | WARN **29** | 25 observed + 4 filings remain, all outside a series or in a rename gap |
| D-16 | **FAIL** (2 in scope) | PASS; global 116 → **99** | NSE files demergers as "Scheme Of Arrangement"; the parser now reads them |
| D-18 | PASS (136 logged) | PASS (**303** logged: 238 measured, 62 ignored, 3 gap-skipped) | |
| D-19 | **FAIL** (2 in scope) | PASS; global skips 51 → **29** | the issue price was in the filing subject all along |
| D-24 | **FAIL** (4 windows) | PASS | spells repointed to HEXAWARE / ORCHIDPHAR / KBL; GUJENERGY's series extended to 2015 |
| D-36 | WARN 18,102 | WARN 18,049 | |
| D-37 | WARN 279 (10 in scope) | WARN **234** (14 in scope) | see below — nothing changed by design |
| D-39/40/41 | PASS / WARN 55 / WARN 17 | unchanged | one stale file (`SEINVEST`) restored to `extra_targets.csv` |

Corporate-action table: 26,044 → 26,131 rows; demerger 110 → **237**, rights 350 → 367,
`kite-observed` 118 → **63** (35 rejected for want of a raw-series break, 20 superseded by the
filings now parsed). `qa/observed_events_rejected.csv` is new.

### New reference figures

Both books re-run with `scripts/run_rebuilt_book.py --book <b> --start 2010-01-01`. The **old**
column is not the figure quoted in §23 — it is a fresh run against a shadow copy of the pre-repair
store (`corporate_actions.csv` and `membership/nifty250.csv` from the 2026-09-12 backup, the
adjusted views rebuilt by the pre-repair `build_adjusted.py` from git `HEAD`). That control
reproduced the §23 decision line **exactly** (mm_v1 23.5% / −26.3%, om25_v4 22.6% / −28.3%, 1,873
and 1,681 trades), so every difference below is the data, not the engine.

| Book | Window | CAGR old → new | Sharpe old → new | Max DD old → new |
|---|---|---|---|---|
| `mm_v1` | 2010-26 | 23.52% → **23.52%** | 1.149 → **1.149** | −26.26% → **−26.36%** |
| `mm_v1` | 2016-26 | 25.85% → **26.02%** | 1.186 → **1.197** | −26.26% → **−26.36%** |
| `om25_v4` | 2010-26 | 22.59% → **22.74%** | 1.198 → **1.222** | −28.32% → **−26.24%** |
| `om25_v4` | 2016-26 | 23.45% → **23.61%** | 1.146 → **1.168** | −28.32% → **−26.24%** |

(2016-26 computed from the run's own equity file with `compute_dashboard_metrics`, so it is the same
convention as the headline. Trades: mm_v1 1,873 → 1,880; om25_v4 1,681 → 1,685.)

`REFERENCE` in `tests/_harness.py` is updated to `mm_v1 (0.235, -0.264)` and
`om25_v4 (0.227, -0.262)`; H-07 fails by construction on the old values, as the brief expected. The
pre-repair pair is kept in the comment beside it.

**The OM25 drawdown improvement is a peak change, not a trough change.** Both bases bottom on
2020-03-23. The old book's drawdown ran from a 2018-08-28 peak; the repaired book made a new high on
2020-02-20 first, so the same COVID trough measures −26.2% instead of −28.3%. `mm_v1`'s worst
drawdown is unmoved in date (2025-03-04) and 10 bp deeper.

**Why the books moved at all.** 122 more demergers and 17 more rights issues are now adjusted, and
about 550 previously dropped `observed:` events are applied, so the 252-session score changed for
many names and the marginal picks at rank 45 reshuffled. `mm_v1` diverges on 60 trade legs over 27
symbols from 2013-10-03; `om25_v4` on 272 legs over 106 symbols from 2010-06-02 — its rank-blend
score is the more sensitive of the two. Neither book's rules, sizing or timing changed.

### Held-name impact of the bad prints

Of the seven names named in the brief — ADANIENT, CGPOWER, CONCOR, MFSL, JSL, CANBK, TATASTEEL —
**exactly one position was open across an affected ex-date in sixteen years**:

| Book | Symbol | Entry | Exit | Event crossed | P&L old | P&L new |
|---|---|---|---|---|---|---|
| `mm_v1` | TATASTEEL | 2017-10-04 | 2018-03-05 (rank) | rights 2018-01-31 | **−0.03%** | **+4.93%** |

The +4.96 pp is precisely the ex-rights factor (1 / 0.95274 − 1 = +4.96%): the trade's entry, exit,
share count and dates are identical, only the price basis moved. `om25_v4` held none of the seven
across an affected date. The 2015-2016 events (ADANIENT, CGPOWER, CONCOR, MFSL, JSL) fall in years
when neither book held those names, so the phantom −61% to −83% days never hit a position directly —
they did their damage indirectly, by wrecking the 252-day momentum of those names for a year
afterwards and so distorting the ranking the books picked from. CANBK's only holding (2026-04-02 →
2026-07-02, +1.48%) is nine years after its rights issue and unchanged.

One repaired name did change what the books bought: with GUJENERGY's price series restored to
2015-09-15, `om25_v4` first buys it on **2017-05-03** instead of 2020-02-03 (10 legs instead of 6)
and `mm_v1` a month earlier than before.

### What still needs a decision

1. **C-04** — the trailing-stop peak convention. Unchanged by this work; still the founder's call
   (amend MECHANICS to the engine's convention, recommended, or change the engine and re-baseline
   again).
2. **D-37 — the demerger factor convention.** Explained with a worked Vedanta example in
   `REPAIRS.md` §7. Recommendation: **keep the measured convention**; the alternative prints a
   −25% to −33% day on 238 events and stops the books out of every demerging holding on a loss the
   holder did not take. Two audit additions are proposed there, neither of which changes a number.
3. **TATASTEEL's 2007-10-29 rights** (1:5 @ Rs 290 premium, Rs 10 face) is filed without a price and
   is still unadjusted — unchanged by this repair, seven years before the book era, and it would
   need a hand-entered row rather than a parser fix. Founder's call.
4. **Kite's 2015-01-01 step cluster** (CGPOWER, CONCOR, MASTEK, TCI, KTKBANK, ASHIMASYN) is a defect
   in Zerodha's own history, not the store's. Worth raising with them; until then the store
   deliberately disagrees with Kite on those dates.
5. **D-38 stays skipped** — the two runs were written to a scratch directory, so there is still no
   `data/<book>_portfolios/latest.json` locally to scope the held-name Kite check to.

## Founder decisions 2026-09-12

- C-04 (stop peak): the mechanics wording is amended to the engine's convention — the peak is the highest
  close from the session after entry onward (the entry session's close joins the peak the next session);
  no engine change, the locked record stands. The test now checks that convention.
- D-37 (demerger factor convention): keep the store's measured factor (raw ex/cum ratio). Kite's ratio is
  not adopted; the two audit additions in REPAIRS.md §7 (log both factors; cross-check against the
  spin-off's first traded value) go on the fortnightly list.
- Deploy: fixes, store repair and re-baseline go live in one merge; on Railway the repaired membership
  and corporate-action metadata are uploaded, the nightly rebuilds the views, both books rerun with a
  full trade-log rebuild.
