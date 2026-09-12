# REPAIRS — master-store repair for the four data-suite failures, 2026-09-12

Scope: the four failures of the first data-suite run (`RESULTS.md` → "Data suite — first run
2026-09-12"): D-14, D-16, D-19, D-24. Plus the founder-facing explanation of the D-37 warning,
which is **not** changed. Local only — `data/master`, `data_pipeline/master_store/`,
`tasks/book_verification_2026/tests/_harness.py` and one new file under `tests/`. Nothing was
deployed, no LOCKED config or rule was touched, and no factor, ratio, price or date in this
document was invented: every value is either read off the store's own raw layer or cited below.

**Result: 42 data tests — 41 pass, 1 skipped (D-38), 0 fail.** No test was recalibrated.

## Summary of what turned out to be wrong

Three of the four failures were one root cause each in the store's code, not the data gaps the
first run diagnosed:

1. **D-14** was the collection bug the brief described, *plus* a second one behind it: applying the
   dropped rows as they stood would have written four false factors into the store, because
   Kite's own day-candle history carries misdated steps.
2. **D-16** was not a missing filing. NSE **does** file both events, as
   `Scheme Of Arrangement`, and `build_corporate_actions.parse()` only recognised the literal word
   `demerger`. The same parser gap hid **127 other demerger filings**, which is most of the store's
   116 unexplained >50% one-day moves.
3. **D-19** was not a missing issue price either. Both filings carry it in the subject line; the
   rights regex required the word "premium" spelt out and immediately after the ratio.
4. **D-24** was the canonical-symbol / identity problem the brief described, in four different
   shapes, one of which needed a price series the store had never exported.

Because each repair is a parser or collection fix rather than a hand-entered row, the nightly
reproduces all of it: `build_corporate_actions` → `derive_observed_events` →
`build_corporate_actions` (one extra pass to fixpoint) → `build_adjusted` → panel views → QA.

---

## 1. D-14 — `observed:` corporate actions were never applied

### The collection bug (as briefed)

`build_adjusted.main()` collected a company's events by the ISIN each identity window carried and
fell back to the ticker **only for windows whose ISIN was unknown**. Every row
`derive_observed_events.py` writes carries no ISIN, so for any company with a filing history —
which is every index member — the inferred event was silently dropped: 576 events on 164 symbols,
four of them on current Nifty 250 members inside the book era.

**Fix** (`data_pipeline/master_store/build_adjusted.py`): a row with an ISIN is matched by ISIN, a
row without one by ticker inside the window that ticker traded. The ISIN bound was also widened
from the window to the **company's** span, because an ISIN belongs to one company and a scheme that
suspends a ticker for months files its ex-date in the gap between two windows (this is what
surfaced as the new D-18 failure on `EASTSILK 2024-11-22` mid-repair).

**Dedupe** (`drop_observed_covered_by_filing`): one event can arrive both as a filing and as an
observed row. The filing wins — it carries the ISIN, the ratio and the exact ex-date, while the
observed row's date is read off a price step and its *type* is a guess. Match on ticker plus
ex-date within 6 days. Without this the repair would have double-applied Adani Enterprises' 2015
demerger (filed as a scheme of arrangement, observed as a 0.297 "split"): 0.297 × 0.172 = 0.051.

**Unit test**: `tests/test_build_adjusted_events.py` — 5 tests on a synthetic 8-session store.
Test 1 (the fallback) fails on the pre-repair module and passes now, verified directly. Test 2 (the
dedupe) is the guard on the new risk the fix creates.

### The second bug: Kite's history carries misdated steps

Applying the 576 dropped rows as they stood would have been wrong. Of the four in-scope failures,
**two were not corporate actions at all**:

| Row | Raw (bhavcopy) close across the ex-date | Verdict |
|---|---|---|
| CGPOWER 2015-01-01 split 0.341263 | 188.05 → 186.55, i.e. −0.8% | no share event |
| CONCOR 2015-01-01 split 0.800000 | 1,353.00 → 1,357.90, i.e. +0.4% | no share event |

A share-count event changes the number of shares, so it **must** break the unadjusted series by the
same ratio. Kite's series for these names steps by 2.93x and 1.25x at 2015-01-01 while the raw
series runs straight through. The same date recurs for MASTEK (0.342), TCI (0.543) and KTKBANK
(0.815), and in two of those the factor is almost exactly that of a *later* real event (MASTEK's
Majesco demerger, measured 0.340 on 2015-06-12; TCI's demerger, measured 0.530 on 2016-08-26): a
cluster in which Kite applied a later event's factor to pre-2015 candles only.

**Fix** (`derive_observed_events.py::raw_corroborates`): a kite-observed candidate is accepted only
when the raw series breaks across the candidate date (± 3 sessions) by at least **half** the move
the factor implies. The half tolerates the market's own move on the ex-date and a demerger whose
measured ratio differs from Kite's factor. 35 candidates are rejected and written to
`qa/observed_events_rejected.csv` with the reason `no-raw-break`; the kite-observed population goes
118 → 63 rows in the CA table (the other 20 are now suppressed by the existing `has_filing` guard,
because the demerger filings behind them are finally parsed).

The other two in-scope failures were real events mis-typed as splits: **ADANIENT 2015-06-03** and
**MFSL 2016-01-27** are demergers, now carried as `demerger` rows from NSE's own feed (see §2) and
measured the way every other demerger in the table is.

### Effect

| | before | after |
|---|---|---|
| D-14 in-scope unapplied events | 4 | **0** |
| D-15 population (all symbols, all history) | 576 (572 observed, 4 filings) | **29** (25 observed, 4 filings) |

The four remaining filing-side rows and the 25 observed ones are the residue listed in §5.

---

## 2. D-16 — the two "missing" demergers are in NSE's feed, filed as schemes of arrangement

`data/master/raw/nse_ca/` already holds both filings. `build_corporate_actions.parse()` tested
`if "demerger" in subject.lower()`, so neither was typed:

```
JSL      19-Nov-2015  ' Composite Scheme Of Arrangement'  isin=INE220G01021  fv=2  series=EQ
CGPOWER  15-Mar-2016  ' Scheme Of Arrangement'            isin=INE067A01029  fv=2  series=EQ
```

Both events were confirmed independently before the parser was changed:

- **Jindal Stainless (JSL), ex-date 2015-11-19.** Composite Scheme of Arrangement among JSL,
  Jindal Stainless (Hisar) Ltd, Jindal United Steel Ltd and Jindal Coke Ltd: the ferro alloys and
  mining divisions demerged into JSHL at a **1:1 share entitlement ratio**, plus slump sales of the
  Hisar stainless plant (~Rs 2,809 cr), the Odisha hot strip plant (~Rs 2,413 cr) and the Odisha
  coke oven plant (~Rs 493 cr). Sanctioned by the High Court of Punjab & Haryana on 2015-09-21
  (modified 2015-10-12), certified copy filed with the ROC on 2015-11-01.
  Source: <https://www.jindalstainless.com/press-releases/deck-clear-for-jindal-stainles-limited-restructural/>
  ("the shareholders of the Company will be issued shares by Jindal Stainless (Hisar) Ltd as per the
  share entitlement ratio of 1:1").
- **Crompton Greaves (CGPOWER), ex-date 2016-03-15.** Consumer products business demerged into
  Crompton Greaves Consumer Electricals, **1 share of CCPL for every 1 share held**, record date
  2016-03-16, scheme approved by the Bombay High Court. Sources:
  <https://www.business-standard.com/article/markets/crompton-greaves-turns-ex-demerger-116031500192_1.html>
  ("Crompton Greaves traded ex-demerger of its consumer products business with effect from March 15,
  2016"; record date March 16, 2016; 1:1 entitlement) and
  <https://www.sesgovernance.com/pdf/home-reports/Crompton%20Greaves%20Limited_CCPL%20DEMERGER.pdf>.

**No factor was entered by hand for either.** Demerger rows in this table carry no ratio
(`factor_or_amount` is empty for all 237 of them); `build_adjusted` *measures* the factor from the
raw ex/cum close ratio, which is the store's documented convention (see §6). The measured values
are `JSL 0.39130` and `CGPOWER 0.28332`, both now in `qa/adjustment_log.csv` as `measured`.

**Fix** (`build_corporate_actions.py`): `RE_DEMERGER` matches the whole vocabulary NSE actually
uses — `demerger`, `arrangement` / `arangement` / `arngment` / `arngmnt` (the abbreviated forms),
and `capital reduction`. A filing that also parses as a **share-count** event does not get a
demerger row, because that event already carries the factor ("Bonus 4:5 (Pursuant To Scheme Of
Amalgamation)"); a dividend on the same filing does not suppress it. Plain `Scheme Of Amalgamation`
with no "arrangement" is excluded — a merger does not distribute value out of the listed line.

This takes the demerger rows from 110 to **237**, of which 238 log lines are `measured` (was 116),
62 `ignored:<5%` (was 20) and 3 `skipped:gap-*` (new, see below). The added events are
overwhelmingly well-known demergers: Bajaj Auto/Bajaj Holdings 2008-03-14, Wipro 2013-04-09,
Adani Enterprises 2015-06-03 and 2018-09-06, Mastek/Majesco 2015-06-12, Max India 2016-01-27,
Grasim/Aditya Birla Capital 2017-07-19, IIFL 2019-05-30, KPIT/Birlasoft 2019-01-24,
Sun Pharma/SPARC 2007-04-23, Piramal 2008-02-15, CESC 2018-10-30, Sundaram Finance 2018-02-01.

**One guard added with it.** A demerger whose cum and ex rows are more than 10 calendar days apart
is not measured — the "ex/cum ratio" would be months of market move as well as the event. It is
logged as `skipped:gap-<n>d` instead of silently skipped, so D-18 still sees it: `EASTSILK
2024-11-22` (530-day suspension) and `HINDMOTOR/HINDMOTORS 2011-01-27` (27 days).

### Effect

| | before | after |
|---|---|---|
| D-16 in-scope unexplained >50% moves | 2 (JSL, CGPOWER) | **0** |
| D-16 global count | 116 | **99** |

---

## 3. D-19 — both rights issues carry their issue price in the filing

The subject lines in `corporate_actions.csv` already read:

```
CANBK     2017-02-17  Rights 1:10 @ Prem Rs 197/- Per Share
TATASTEEL 2018-01-31  Rights - 4:25 Fully Paid Up Shares @ Premium Rs 500/- Per Share /
                      2:25 Partly Paid Up Shares @ Premium Rs 605/- Per Share
```

`RE_RIGHTS` required `premium` spelt in full and immediately after the ratio, so both parsed as
`@prem=None` → `event_factor` returned 1.0 and logged `rights:no-price`.

**Fix** (`build_corporate_actions.py`): the ratio and the price clause are matched separately. The
price clause is searched in the text after the ratio, up to the first `/` — which is both the
separator NSE uses between tranches and the `/-` of a rupee amount. `prem`, `prem.`, `premium`,
`Prem@Rs`, `@Prem Rs` and a bare `At Par` (premium zero) are all accepted, and the ratio may carry
a decimal (`1:11.10`). 17 further rights rows become priced; `rights:no-price` goes 44 → 22.

### Face value as of the ex-date

NSE's feed reports `faceVal` **as of the fetch**, not as of the ex-date — CANBK's 2005 rows already
say `2`, and its face value only went Rs 10 → Rs 2 on 2024-05-15. Using the row's own face value
would price the 2017 rights at Rs 2 + 197 instead of Rs 10 + 197.

**Fix** (`build_adjusted.py::face_value_at_ex`): only splits and consolidations change the face
value, and by the same ratio as the price, so the face value in force at a row's ex-date is today's
face value divided by the factors of the split/consolidation rows that came *after* it. Derived
from the store's own table, nothing entered by hand:

- CANBK: 2 ÷ 0.2 (`Face Value Split ... From Rs 10/- Per Share To Rs 2/- Per Share`, 2024-05-15) = **Rs 10**
- TATASTEEL: 1 ÷ 0.1 (`... From Rs 10/- Per Share To Re 1/-`, 2022-07-28) = **Rs 10**

### The two factors

Both use the table's own rights formula, `f = (b·P_cum + a·issue) / ((a+b)·P_cum)`, with `P_cum`
the raw close on the cum day:

| Symbol | Ratio a:b | Face | Premium | Issue price | P_cum | Factor | Applied |
|---|---|---|---|---|---|---|---|
| CANBK 2017-02-17 | 1:10 | 10 | 197 | **207** | 296.05 (2017-02-16) | **0.972655** | yes |
| TATASTEEL 2018-01-31 | 4:25 | 10 | 500 | **510** | 775.85 (2018-01-30) | **0.952740** | yes |

Sources for the terms, independent of the store:

- **Canara Bank**: "equity shares at a price of Rs 207 per share (including a premium of Rs 197) on
  a rights basis in the ratio of 1 equity share for every 10 fully paid up equity shares held on
  the record date of February 20, 2017 … 5,42,99,105 equity shares of face value of Rs 10 each",
  <https://www.canarabank.bank.in/documents/d/guest/5-abridged-letter-of-offer-canara-bank-final>
  and <https://www.business-standard.com/article/finance/canara-bank-s-rs-1-124-cr-rights-issue-to-open-on-march-2-117022000542_1.html>.
- **Tata Steel**: the rights history at
  <https://trendlyne.com/equity/rights/TATASTEEL/1366/tata-steel-ltd-rights/> lists both tranches
  on the same ex-date with the face value of the time — "31 Jan 2018 | 4.0:25.0 | 10.0 | 500.0 |
  01 Feb 2018" and "31 Jan 2018 | 2.0:25.0 | 10.0 | 605.0 | 01 Feb 2018". Ex-rights date confirmed
  by <https://www.business-standard.com/article/markets/tata-steel-trades-ex-rights-stock-hits-52-week-high-118013100168_1.html>
  (2018-01-31), record date 2018-02-01.

**Which Tata Steel tranche, and why.** The **fully paid tranche (4:25 @ Rs 510)** is the one
applied. Three reasons: (a) the store's price file follows the fully paid line, and the partly paid
entitlement listed and traded as a **separate security** whose market value is not in the store;
(b) the table's formula models one ratio and one issue price, and there is no filed value for a
partly-paid share at the ex-date — only Rs 154 (25%) was payable on application, so treating the
tranche at its full Rs 615 would be an assumption about a future call, not a filed fact; (c) it
errs towards **under**-adjusting, which leaves a small residual loss in the series rather than
manufacturing a gain. For the record, the both-tranche generalisation
`f = (P_cum + Σ (a_i/b_i)·issue_i) / (1 + Σ a_i/b_i)` gives **0.942413** on the same cum price —
1.1 pp more adjustment. The actual raw move on the ex-date was −9.1% (775.85 → 705.05), so neither
convention explains all of it; the rest is the market.

### Effect

| | before | after |
|---|---|---|
| D-19 in-scope unadjusted rights | 2 | **0** |
| `qa/adjustment_log.csv` skips (global) | 51 (44 rights + 7 dividends) | **29** (22 rights + 7 dividends) |

---

## 4. D-24 — four Nifty 250 spells on the wrong listed line

Each spell was traced to the ticker the company actually traded under, using
`symbol_master.csv` windows, `isin_names.csv` filing names, `symbol_changes.csv`, and — the
strongest check available — the `nse500` membership file, which already carries three of the four
spells on the correct line. All four repairs are in `identity.py`; nothing was hand-edited in
`membership/*.csv` (those files are regenerated by `emit_pit_membership.py`).

| Spell (nifty250) | Was | Now | Evidence |
|---|---|---|---|
| 2005-09-25 → 2008-03-14 | HEXT (file starts 2025-02-19) | **HEXAWARE** (2005-01-03 → 2020-10-30) | ISIN INE093A01033 → INE093A01041; both filed as "Hexaware Technologies Limited"; taken private 2020-10-30, re-listed 2025-02-19. `nse500` already carries this era as HEXAWARE (2003-04-01 → 2020-09-25). |
| 2005-09-25 → 2009-03-27 | ORCHPHARMA (file starts 2020-11-03) | **ORCHIDPHAR** (2005-01-03 → 2019-07-24) | ISIN INE191A01019 (ORCHIDCHEM → ORCHIDPHAR, renamed 2015-12-21) → INE191A01027 on the post-IBC re-listing. `nse500` already carries this era as ORCHIDPHAR (2005-01-03 → 2015-09-28). |
| 2006-09-01 → 2009-10-22 | KIRLOSBROS (file starts 2010-04-20) | **KBL** (2006-04-07 → 2010-03-08, series newly exported) | ISIN INE732A01028 → INE732A01036; `isin_names.csv` has both as "Kirloskar Brothers Limited"; the CA table carries KBL dividend filings 2006-2009 under INE732A01028. `nse500`'s equivalent spell ends 2010-03-09, exactly the KBL window's end. |
| 2016-04-01 → 2026-03-30 | GUJENERGY (file started 2019-01-16) | **GUJENERGY**, series extended to 2015-09-15 | the ticker GUJGASLTD changed ISIN INE844O01022 → INE844O01030 on 2019-01-16 with no gap and no rename; nothing joined the two windows, so the canonical series started at the ISIN change. |

Three mechanisms were used, and the choice in each case was deliberate:

- **`LINE_OVERRIDES`** (HEXT, ORCHPHARMA, KIRLOSBROS) — the spell is repointed at the historical
  ticker and the two listed lines stay **separate**. For HEXT this matters: it is a current Nifty
  250 member, and merging HEXAWARE's 2005-2020 history onto it would put a four-year hole in a
  series the panel loader forward-fills. For KIRLOSBROS the KBL and KIRLOSBROS windows are six
  weeks and +29% apart (KBL 2010-03-08 at 260.55, KIRLOSBROS 2010-04-20 at 337.35), so joining them
  would write a phantom return into the series. Both non-joins are recorded as explicit `NOT (...)`
  comments in `HAND_RENAMES` beside the existing `NOT ("MAX","MAXIND")` note.
- **New series export** (KBL) — `KBL` had no price file because it was in no target list; adding
  the membership row makes it one, and `export_bhavcopy_series` wrote 966 sessions
  (2006-04-07 → 2010-03-08) from the bhavcopy archive. No data was fabricated; the rows were
  already in `bhavcopy_eq.parquet`.
- **New `ISIN_CHANGES` list in `identity.py`** (GUJGASLTD) — one ticker, two ISINs, contiguous
  sessions, no rename to follow, so neither ISIN matching nor a rename edge could join them. The
  edge mechanism is the existing one; the list is separate from `HAND_RENAMES` because it is not a
  rename. `GUJENERGY.csv` now spans 2015-09-15 → 2026-09-09 (2,720 sessions, was 1,897).

**Known gaps, not repaired** (recorded rather than fabricated): `nse500` still references
**BAGMANE** (staged for the 2026-09-30 reconstitution, not yet listed) and **GTNINDS** with no
price file, plus 17 uncovered `nse500` windows and 1 `nifty100` window — all pre-2008 delisted
lines the store never fetched. These are the D-24 warn side and the D-40 manifest orphans; they are
unchanged and outside the Nifty 250 the books read.

### Effect

D-24's hard `nifty250` assertion passes. The visible consequence for the books: GUJENERGY becomes
rankable from 2016 instead of 2020, and `om25_v4` first buys it on **2017-05-03** instead of
2020-02-03 (10 legs instead of 6).

---

## 5. Store housekeeping the re-export exposed

`prices/bhavcopy/SEINVEST.csv` (written 2026-09-11) was on disk but no longer in any target list,
so the re-exported manifest dropped it and D-39 went red. Rather than delete a price series,
`SEINVEST` was restored to `data/master/extra_targets.csv` — the additive target list the store
already uses for non-member symbols — so the manifest documents the file it holds. It is a
delisted-2011 microcap in no index; nothing reads it.

## 6. Unresolved — recorded, not invented

- **22 `rights:no-price` rows remain** (about 14 distinct events across alias keys): ALOKINDS /
  ALOKTEXT 2013-02-15, ANDHRAPAP / APPAPER / IPAPPM 2010-02-23, BAJAUTOFIN / BAJFINANCE
  2006-11-13, DCB / DCBBANK 2006-01-17, JMCPROJECT 2016-01-11, LAKSHVILAS 2006-11-17, OCL
  2006-08-29, ORIENTPPR 2007-06-08, PATINTLOG 2021-02-17 and 2021-10-28, SIGMAADV 2021-07-12,
  SINTEX 2016-08-08, TATAMOTORS / TMPV 2008-09-09, TATASTEEL / TISCO 2007-10-29, UNIWESTBNK
  2006-01-17. Every one of these filings states a ratio and **no price**, so no factor can be
  derived from the store. None is a current Nifty 250 member inside the book era, which is why
  D-19 is green. One has a citable price but is deliberately left alone: **TATASTEEL 2007-10-29**,
  filed as `Right-Eq1:5 & 9ccps:10eq`, was 1:5 at a premium of Rs 290 on a Rs 10 face value
  (<https://trendlyne.com/equity/rights/TATASTEEL/1366/tata-steel-ltd-rights/>). It is unadjusted
  both before and after this repair (−8.63% on the ex-date in both bases), it is seven years before
  the book era, and applying it would need a hand-entered row rather than a parser fix. Flagged for
  the founder.
- **3 demergers skipped for a suspension gap**: EASTSILK 2024-11-22 (530 days), HINDMOTOR /
  HINDMOTORS 2011-01-27 (27 days). Logged, not measured — measuring across the gap would invent a
  factor out of months of market move.
- **29 share events still show no factor step** (D-15, down from 576): 25 observed rows and 4 NSE
  filings, first symbols ACKRUTI, AMBUJACEM, ARHAMFISCL, BSOFT, COREEDUTEC, COROMANDEL, DALMIASUG,
  DCMSHRIRAM, DEWANHOUS, HCC. These are events whose ex-date falls outside the symbol's series or
  in a rename gap. Not triaged; the count is 5% of what it was and well inside the D-15 cap.
- **99 unexplained >50% one-day moves remain globally** (D-16, down from 116), none on a current
  Nifty 250 member inside the book era.
- **35 Kite steps rejected as artefacts** are in `qa/observed_events_rejected.csv`. The 2015-01-01
  cluster (CGPOWER, CONCOR, MASTEK, TCI, KTKBANK, ASHIMASYN) is a defect in Kite's own history, not
  in the store. It is worth raising with Zerodha; until then the store deliberately disagrees with
  Kite on those dates, which is why they now appear in the D-37 warning as `no-ca-row`.

---

## 7. D-37 — the demerger factor convention (nothing changed; explanation for the founder)

### What the store does, and how it measures it

A demerger filing carries no ratio — all 237 rows in `corporate_actions.csv` have an empty
`factor_or_amount`. So `build_adjusted` **measures** the factor: it is the raw (unadjusted)
bhavcopy close on the first session on or after the ex-date, divided by the raw close on the session
before it, applied to all history before the ex-date, and only when the fall is more than 5%
(below that the filing was a non-event for the listed line). Every decision is written to
`qa/adjustment_log.csv` as `measured` or `ignored:<5%`.

### A worked example: Vedanta, ex-date 2026-04-30

```
                 raw close   store adj close   store factor   Kite close   Kite/raw
2026-04-29        773.60         271.55          0.351021       404.90      0.5234
2026-04-30        271.55         271.55          1.000000       271.55      1.0000
                                 0.00% day                     −32.93% day
```

- **The store's factor is 0.351021** = 271.55 / 773.60. All of Vedanta's history before 2026-04-30
  is scaled by it, and the adjusted series shows **exactly 0.00%** across the ex-date. The whole
  ex-day fall is treated as value that left the company.
- **Kite's factor for the same event is 0.5234** — read off the step in `kite close / raw close`,
  which runs at 0.52340 until 2026-04-29 and 1.00000 from 2026-04-30. Kite's own series therefore
  shows **−32.93%** across the ex-date. The ratio between the two conventions is
  0.5234 / 0.35102 = **1.491**, which is the "VEDL 2026-04-28 1.491" line in the D-37 warning.
  (SIEMENS 2025-04-07 is the same shape: store 0.57069, Kite 0.7618, ratio 1.335, Kite's series
  −25.09% on the ex-date against the store's 0.00%.)
- **Why they differ.** The store measures a *value* ratio from the market's own repricing on the
  ex-date. Kite applies a *fixed* factor per event. I have not found a published NSE circular
  stating Kite's number, so I can only say what it is — 0.5234 measured from Kite's series — not
  where it comes from; the first run's note that Kite "uses the official entitlement ratio" is a
  plausible reading of a 1:1-type entitlement, not something verified. Treat the provenance as
  open.

### What each convention implies for a momentum book

The store's price-return panel has **one column per listed line**. Neither convention books the
spin-off shares as an asset — the book cannot hold them. That asymmetry is what decides the
question:

- **Measured (what the store does).** The ex-date is invisible. A held position marks 0% across it,
  the 20% trailing stop is not touched, and the 252-session momentum score afterwards is the
  surviving company's own path with no one-day artefact. The cost: the factor absorbs that day's
  market move as well as the event, and it implicitly assumes the spin-off was worth exactly the
  fall. If the spin-off was worth less, the book's return is flattered by the difference.
- **A fixed entitlement-style factor (what Kite's series implies).** Vedanta would print a −32.9%
  day and Siemens a −25.1% day in the middle of the book's lookback. With a 20% trailing stop
  checked at the monthly signal, **any holding across a demerger is stopped out on the next signal
  date**, on a loss the holder did not suffer — they received the spin-off shares. The name's
  252-day momentum then stays depressed for a year, so the book systematically evicts and avoids
  demerging companies. On the six large current members in the D-37 list the gap is 13% to 53%.

### Recommendation

**Keep the measured convention.** It is the only one that does not manufacture a loss for a book
that cannot hold the spin-off, and switching would re-introduce a phantom −25% to −33% day on 238
events including Vedanta, Siemens, Tata Motors PV, NMDC, Motherson and Tata Communications. Two
additions are worth making, neither of which changes a number today:

1. Record **both** factors in `qa/adjustment_log.csv` — the measured ratio and the step Kite
   applied — so the divergence is auditable per event instead of being re-derived each time.
2. Where the spin-off's own line exists in the store, cross-check the measured factor at the next
   reconstitution against `(parent ex value + spin-off first-traded value) / parent cum value`. That
   is the only way to tell whether the measured convention over- or under-states a given event, and
   it needs no change to the adjustment pass.

The residual risk of the measured convention is a filing that coincides with a genuine >5% market
fall, which would be adjusted away as if it were a distribution. That risk is bounded by the 5%
floor and visible in the log; it did not move any in-scope test in this repair.

---

## 8. Files changed

| File | Change |
|---|---|
| `data_pipeline/master_store/build_corporate_actions.py` | demerger vocabulary (`RE_DEMERGER`), rights ratio/price parsed separately (`RE_RIGHTS`, `RE_RIGHTS_PREM`, `RE_RIGHTS_PAR`), decimal ratios |
| `data_pipeline/master_store/derive_observed_events.py` | `raw_corroborates` guard; `qa/observed_events_rejected.csv` |
| `data_pipeline/master_store/build_adjusted.py` | collection by ISIN-or-ticker, ISIN bound widened to the company span, `drop_observed_covered_by_filing`, `face_value_at_ex`, `skipped:gap-<n>d` for demergers across a suspension |
| `data_pipeline/master_store/identity.py` | `ISIN_CHANGES` (GUJGASLTD 2019-01-16), `LINE_OVERRIDES` for HEXT / ORCHPHARMA / KIRLOSBROS, two `NOT (...)` notes |
| `tests/test_build_adjusted_events.py` | new — 5 tests: the fallback, the dedupe, and the ex-date face value |
| `tasks/book_verification_2026/tests/_harness.py` | `REFERENCE` re-baselined (§ RESULTS.md) |
| `data/master/extra_targets.csv` | `SEINVEST` restored so the manifest covers the file on disk |
| `data/master/` derived files | `corporate_actions.csv`, `qa/observed_events.csv`, `qa/observed_events_rejected.csv`, `qa/adjustment_log.csv`, `qa/bad_prints.csv`, `qa/report.md`, `membership/*.csv`, `prices/bhavcopy/*`, `prices/bhavcopy_manifest.json`, `prices/adjusted_pr/*`, `prices/adjusted_tr/*` — all regenerated by the pipeline, none hand-edited |

Rebuild command used (the nightly's own steps):

```
python -m data_pipeline.master_store.emit_pit_membership
python -m data_pipeline.master_store.export_bhavcopy_series
python -m data_pipeline.master_store.derive_observed_events
python -m data_pipeline.master_store.build_corporate_actions
PYTHONPATH=. python scripts/refresh_master_store.py --steps adjust,qa
```

(`build_corporate_actions` and `derive_observed_events` read each other's output, so they need one
extra alternating pass to reach a fixpoint after a parser change. Reached here in two passes.)
