# Results

## Phase 1 — symbol master (2026-09-10, gate not yet met for 2006-2007)

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

Coverage, minimum over event dates, counting each member once against the
index's fixed size:

| Year | Nifty 50 | Nifty 100 | LargeMidcap 250 | Nifty 500 |
|---|---|---|---|---|
| 2006 | 96.0 | 95.0 | **92.4** | **92.4** |
| 2007 | 98.0 | 96.0 | **93.2** | **94.0** |
| 2008 | 100 | 98.0 | 96.4 | 95.6 |
| 2010 | 100 | 100 | 98.4 | 96.2 |
| 2013 | 100 | 100 | 98.4 | 97.2 |
| 2016 | 100 | 99.0 | 98.4 | **97.8** |
| 2019 | 100 | 99.0 | 98.8 | 98.6 |
| 2020+ | 100 | 99-100 | 99.6-100 | 99.8-100 |

Gate status: **2020-2026 ≥ 99% met. 2016-2019 ≥ 98% missed by one name
(Nifty 500, 2016: 97.8). 2006-2015 ≥ 95% missed in 2006-2007 on the two
broad indices.** The residue with spells in 2006 or later is 42 names (22
Nifty 500, 14 LargeMidcap 250, 4 Nifty 100, 2 Nifty 50), listed in
`qa_unresolved_2006plus.csv`. Automatic routes are exhausted; each needs
a hand search with evidence, and some will be genuinely unresolvable
(delisted 2006-2010 under a name no NSE master still carries).

An earlier version of the gate over-counted: a company resolved to two
ISINs (face-value change) was counted twice, which showed the Nifty 500 at
101-102% in 2008-2015. Corrected to count each member once.
