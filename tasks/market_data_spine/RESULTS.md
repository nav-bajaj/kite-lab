# Results

## Phase 1 — symbol master (2026-09-10) — GATE MET

Inputs fetched, all from NSE directly, zero errors:

| Source | Rows | Span |
|---|---|---|
| Bhavcopy, daily (4,691 legacy + 664 UDiFF) | 8.9M cash-equity rows, 5,355 sessions | 2005-01-03 → 2026-09-09 |
| Corporate-action filings (107 quarterly files) | 42,427 | 2000-01 → 2026-09 |
| `symbolchange.csv`, `namechange.csv`, `EQUITY_L.csv` | 1,058 / ~2,400 / ~2,100 | NSE masters |

Outputs in `data/master/` (small tables committed; the 186 MB parquet is not):
`symbol_master.csv` (6,001 ISIN×symbol windows, 5,272 ISINs, 17 orphans),
`isin_names.csv` (7,487 names), `symbol_changes.csv`, `symbol_renames_detected.csv`
(665 renames read off PREVCLOSE, 51 absent from NSE's master), `resolution.csv`,
`qa_coverage.csv`, `qa_unresolved_2006plus.csv`.

What it took to chain a member listed under today's ticker back to the
ticker it traded under in 2006 — each step found by looking at the names
that failed, not by design:

1. The bhavcopy's ISIN column only begins **2011-06-22**.
2. The filings API stamps **today's** symbol on every historical filing, so
   it dates ISINs but not old tickers.
3. NSE's `symbolchange.csv` dates 1,058 renames; chained 729 pre-ISIN blocks.
4. It misses corporate restructurings (`BAJAJAUTO→BAJAJHLDNG`, `KPIT→BSOFT`,
   `COLGATE→COLPAL`). The bhavcopy's PREVCLOSE dates those: 665 exact matches.
5. 36 reconstruction leftovers were renamed companies encoded by hand with
   filing evidence (`lib/manual_resolutions.py`); 38 more resolved through
   an expected-symbol hint that the bhavcopy had to confirm. One hint bound
   to the wrong company (`RPGLIFE` for Summit Securities) and was removed.

6. Renames that coincide with a face-value change give the old and new
   ticker DIFFERENT ISINs (`COLGATE` INE259A01014 → `COLPAL` INE259A01022),
   so ISIN alone cannot join them. `lib/identity.py` builds company
   identity as connected components over trading windows joined by shared
   ISIN **and** dated rename edges (NSE master + PREVCLOSE detector + 16
   hand edges): 5,197 companies over 6,001 windows, 1,379 edges joined.
7. Six restructurings where the reconstruction attached a historical member
   to the wrong listed line (the 2006 "Bajaj Auto" is today's BAJAJHLDNG,
   not the 2008 spin-off BAJAJ-AUTO; likewise TIINDIA/TUBEINVEST,
   KPITTECH/KPIT, FLUOROCHEM/GUJFLUORO, GATEWAY/GDL, PIRAMALFIN/PEL,
   MAXIND/MAX) are `LINE_OVERRIDES` in the same file, dated.

Coverage, minimum over event dates, counting each member once against the
index's fixed size, after the identity layer:

| Year | Nifty 50 | Nifty 100 | LargeMidcap 250 | Nifty 500 |
|---|---|---|---|---|
| 2006 | 100 | 100 | 98.0 | 98.2 |
| 2007 | 100 | 100 | 98.0 | 98.4 |
| 2008-2015 | 100 | 100 | 98.8-100 | 98.6-100 |
| 2016-2019 | 100 | 100 (101 = DVR line) | 100 | 100 |
| 2020-2026 | 100 | 100 | 100 | 99.8-100 |

**Gate status: met.** ≥95% from 2006 (worst 98.0), ≥98% from 2016 (worst
100), ≥99% from 2020 (worst 99.8). Before the identity layer the same
numbers read 93.6 / 94.8 for 2006 — the last five points were renames
whose ISIN changed at the same time, invisible to an ISIN join.

Residue with spells in 2006 or later, 8 names, left unresolved with
reasons in `qa_unresolved_2006plus.csv`: Pudumjee Pulp & Paper, Styrolution
ABS (pre-2009 name chain), Summit Securities -Old, Alstom India (LM250
2005-2013; ambiguous between Alstom Projects and Areva T&D lines), Merck
(one spell 2005-09 → 2006-03), Ballarpur and Essar Ports (ISIN known, no
traded window inside the spell). None is in the index after 2014.

An earlier version of the gate over-counted: a company resolved to two
ISINs (face-value change) was counted twice, which showed the Nifty 500 at
101-102% in 2008-2015. Corrected to count each member once.

## Phase 2 — point-in-time membership files (2026-09-10) — GATE MET

`data/master/membership/{nse500,nifty50,nifty100,nifty250}.csv`, loader
schema, keyed by each company's canonical symbol (the ticker it trades
under most recently, which is also the price-file key). Built from the
reconstruction plus Phase 1's resolved leftovers, with the seven line
overrides applied by splitting spells at the cutover. Production
`data/static/*_membership.csv` untouched (D-8).

| Index | Rows | Symbols | Event dates 2006→ | Members, min-max |
|---|---|---|---|---|
| Nifty 500 | 1,633 | 1,258 | 268 | 493-501 |
| LargeMidcap 250 | 773 | 597 | 75 | 246-251 |
| Nifty 100 | 321 | 239 | 74 | 99-101 |
| Nifty 50 | 139 | 123 | 46 | 49-51 |

The shortfall below index size on early dates is the unresolved residue
(Phase 1); the +1 is the Tata Motors DVR line. `lib/validate.py` from the
reconstruction re-run against these files: today exact, 2022 factsheets
exact (the canonical-symbol mapping does not change membership, only keys).
