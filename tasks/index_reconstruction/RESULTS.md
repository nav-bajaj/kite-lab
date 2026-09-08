# Results

Status: four indices reconstructed and validated. Not yet adopted into the
production universe — see the open founder decision at the bottom.

## All four indices, validated three ways

| Index | Span | Events | Today | Mar-2022 factsheet |
|---|---|---|---|---|
| Nifty 500 | 1998-08 .. today | 3,199 | 500/500 exact | **501/501 exact** |
| Nifty 50 | 1996-09 .. today | 222 | 50/50 exact | 50, 49 resolved |
| Nifty 100 | 2003-03 .. today | 459 | 100/100 exact | 100, 99 resolved |
| Nifty LargeMidcap 250 | 2005-09 .. today | 1,049 | 250/250 exact | 250, 247 resolved |

In every case the reconstruction has **zero extra constituents** against the
factsheet. The handful not resolved are companies merged away since — HDFC
into HDFC Bank, MindTree into LTIMindtree, ICICI Securities delisted — which
have no tradeable successor to key a price file on. The membership itself is
exact; only the ticker is unavailable.

The March 2022 factsheets matter because NSE published them independently of
both the event export and the press releases. Matching them tests the chain
in the middle, not just at the endpoint where it was fitted.

## The three smaller indices had to be run backwards

Only the Nifty 500 sheet opens with a seed (all 500 names on 1998-08-01). The
Nifty 50 / 100 / LargeMidcap 250 sheets start mid-stream with balanced
replacements and never state who was in the index at that moment, so their
membership had to be derived by un-applying every event backwards from
today's published list — the approach originally suggested. Each derived seed
lands exactly on the index size (50, 100, 250) with no unapplicable event in
either direction, which is a strong check in itself: a single missing or
mis-joined event would leave the seed off by one.

## Headline

Replaying every Nifty 500 inclusion and exclusion from 1998-08-01 forward
reproduces NSE's published constituent list for 2026-09-08 **exactly**:
500 of 500 symbols, no missing names, no extras, checked through the
production `scripts/universe_membership.py` loader.

```
[1] press releases parsed        : 39
    imbalanced (must be 0)       : 0
[2] replay problems (must be 0)  : 0
[3] dates off expected count     : 0
[4] members_asof(today)          : 500 vs published 500
ALL CHECKS PASSED
```

Coverage: 1998-08-01 to 2026-09-30, 287 event dates, 3,199 events,
1,850 membership spells.

## Why the count check is strong

The Nifty 500 holds a fixed 500 constituents, so the member count is a
continuous invariant across 28 years, not merely an endpoint test. Any
missed exclusion, double-counted inclusion or mis-joined rename shows up
immediately as drift. The final chain sits at exactly 500 on every one of
the 287 event dates, with two documented exceptions — both real:

| Window | Count | Why |
|---|---|---|
| 2016-04-01 .. 2024-08-30 | 501 | Tata Motors 'A' Ordinary (DVR) traded as a second line alongside its parent |
| 2026-09-07 .. | 501 | `DUMMYHEG`, a zero-price placeholder NSE inserts for the HEG graphite demerger |

The DVR case explains the one apparent defect in NSE's own export: the
2016-04-01 reconstitution lists 76 inclusions against 75 exclusions. It is
not a missing row — a second share class of an already-included company
was added, so no one had to leave.

## What the sources actually needed

The raw data does not replay cleanly. Six distinct problems had to be
solved, each found by the count invariant rather than by inspection:

1. **Rename joins (62 cases).** NSE records an exclusion under the company's
   name at exit but the inclusion under its name at entry. Unjoined, each
   leaks a phantom member. 14 sit inside the historical export, 48 straddle
   the 2020 handoff. Every one was verified to be a real member on its event
   date before being encoded, in `lib/renames.py`.
2. **Press-release layout drift.** Section headers are numbered in some years
   and lettered in others (`2) Nifty 500` vs `b) Nifty 500`), upper-case in
   2021 and mixed-case later. Each variant silently returned zero changes and
   cost a semi-annual review until handled.
3. **Multiple Nifty 500 sections per release.** The August 2020 release has an
   eligibility-criteria table headed `NIFTY 500` before the actual
   replacements. Taking the first match found the criteria table and reported
   no changes, dropping the entire September 2020 review.
4. **Wrapped table rows.** Long company names break across three lines,
   leaving the numbered row with an empty name column.
5. **Revocations.** NSE sometimes cancels a published change before it takes
   effect — IREDA's March 2024 inclusion and Vodafone Idea's September 2024
   exclusion were both revoked on impact-cost grounds. Replaying the original
   review alone moves stocks that never moved. Encoded in `lib/revocations.py`.
6. **Corporate actions with no company table.** Two releases list only the
   affected index names (Tata Motors DVR cancellation, HEG demerger), so the
   section parser cannot see them; both are encoded explicitly.

Nothing was fuzzy-matched into place. Fuzzy matching was used only to
*propose* candidates; each was confirmed against the member set on the day,
because the plausible-looking answer was wrong several times — `Procter &
Gamble Health` is the renamed **Merck**, not P&G Hygiene; `Restaurant Brands
Asia` is **Burger King India**; `JSW Dulux` is **Akzo Nobel India**.

## The one genuine data conflict

At the 2020-09-14 handoff the two sources disagree: the historical export
records 1 change that day, the press release 5. The press release is the
fuller record, so the export is cut *strictly before* the handoff. Had the
join been made the other way round, four members would have been silently
wrong from 2020 onward.

## Outputs

| File | Rows | What |
|---|---|---|
| `data/nse500_events_reconstructed.csv` | 3,199 | every inclusion/exclusion with date, symbol, source release |
| `data/nse500_membership_reconstructed.csv` | 1,214 | membership windows in the repo's existing schema |
| `data/unresolved_symbols.csv` | 635 | spells whose company could not be mapped to a symbol |
| `data/pr_nifty500_changes.json` | 39 | parsed press releases, for audit |
| `data/nifty50_membership_reconstructed.csv` | 125 | Nifty 50 windows (161 spells, 36 unresolved) |
| `data/nifty100_membership_reconstructed.csv` | 280 | Nifty 100 windows (335 spells, 55 unresolved) |
| `data/nifty250_membership_reconstructed.csv` | 624 | LargeMidcap 250 windows (775 spells, 151 unresolved) |
| `data/pr_text/` | 128 | extracted release text (PDFs are gitignored, refetchable) |

Rebuild:

```
python3 lib/fetch_press_releases.py     # download PDFs (gitignored)
python3 lib/extract_text.py             # fails loudly on a scan
python3 lib/parse_all_indices.py        # all four indices
python3 lib/emit_membership.py          # Nifty 500
python3 lib/emit_indices.py             # Nifty 50 / 100 / LargeMidcap 250
python3 lib/validate.py                 # Nifty 500 checks
python3 lib/validate_indices.py         # the other three
```

## Symbol coverage, and what it takes to close it

The membership *events* are complete to 1998. The *symbol* mapping is not:
NSE only began printing symbols alongside company names in the press-release
era, so a company that left before ~2020 and is not in today's list has to be
identified some other way.

A second resolution pass recovered 103 more companies, from two sources:

- **The BSE rows of the Kite instruments dump.** The first pass read only NSE
  cash rows, where Kite truncates names to ~25 characters
  ("NETWORK18 MEDIA & INV"). BSE carries the full name, which is what makes a
  match possible at all.
- **Chasing renames forward.** Where a spell closed under an old name, walking
  `renames.py` forward reaches a name today's list does know — that is how
  Sesa Sterlite resolves to VEDL and Prism Cement to PRSMJOHNSN.

Token matching here had to be tightened before it could be trusted. A first
cut that allowed short prefixes and treated "Corporation" as a noise word
mapped **Corporation Bank onto Indian Bank**, **Dena Bank onto D B Corp** and
**Mandhana Industries onto MAN Industries** — all scoring a perfect 1.0. The
rule now requires abbreviations of 4+ characters and full coverage on both
sides. That cost roughly 17 true matches to remove 5 wrong ones, which is the
right trade for a file that feeds backtests. Accepted mappings are frozen in
`lib/backfill_map.py` with the dump name each was matched against, and every
membership row records how its symbol was resolved.

| As of | Members | Symbol known | **Also has price data** |
|---|---|---|---|
| 2010-06-30 | 500 | 358 (72%) | 251 (50%) |
| 2016-06-30 | 501 | 394 (79%) | 311 (62%) |
| 2020-06-30 | 501 | 432 (86%) | 385 (77%) |
| 2022-06-30 | 501 | 456 (91%) | 415 (83%) |
| 2024-06-30 | 501 | 479 (96%) | 463 (92%) |
| 2026-06-30 | 500 | 499 (100%) | 499 (100%) |

The third column is the one that governs whether a survivorship-free backtest
is actually possible, and it is the gap worth closing.

## The price backfill is done

The founder renewed the GDF key on 2026-09-08 and it authenticates. Both
feeds were then used, split by what each can actually serve:

| Feed | Symbols | Why |
|---|---|---|
| Kite | 316 | still listed on NSE; same feed the existing panel was built from, so the adjustment convention matches. Serves day candles back to 2010. |
| GDF | 41 | delisted or BSE-only. Kite's historical API needs an instrument token, which exists only for live instruments, so dead scrips are invisible to it. GDF serves them to their delisting date from a 2009 floor. |

GDF turned out to carry delisted history properly — Allahabad Bank to its
2020 merger, Tata Coffee to 2024, Tata Motors' DVR line to its 2024
cancellation. Sixteen symbols returned nothing even from GDF: pre-2010
delistings and a few REITs.

Written to `nse500_data_backfill/` (Kite) and `nse500_data_backfill_gdf/`
(GDF), both gitignored. **Nothing under `nse500_data/` was touched.**

### Result: every identified symbol now has prices

| Index | 2010 | 2016 | 2020 | 2023 | 2026 |
|---|---|---|---|---|---|
| Nifty 500 | 374/500 | 432/500 | 501/500* | 501/500* | 500/500 |
| Nifty 50 | 44/50 | 50/50 | 50/50 | 50/50 | 50/50 |
| Nifty 100 | 85/100 | 98/100 | 100/100 | 100/100 | 100/100 |
| LargeMidcap 250 | 198/250 | 230/250 | 250/250 | 250/250 | 250/250 |

\* includes the Tata Motors DVR second line.

Symbols-with-prices now equals symbols-identified at every date, so the price
gap is closed. **From 2020 all four indices support a fully survivorship-free
point-in-time universe**; from 2016 the Nifty 50 and Nifty 100 do. What still
binds before that is name-to-symbol resolution for companies delisted long
ago, not missing price history.

### One caveat before stitching

The two feeds do not agree on dividend adjustment. GDF quoted INFY a constant
~2.165% above the Kite panel across a contiguous 14-day window in mid-2026 —
the signature of a dividend applied on one side only. `scripts/apply_corporate
_actions.py` handles splits, bonuses and demergers, not dividends, so it will
not reconcile this. The two backfill directories are therefore kept apart and
must not be blindly concatenated; the 41 GDF series are the ones to treat with
care, and only for dates near their corporate actions.

## What the smaller indices needed on top

- **A scanned press release.** `ind_prs23082021.pdf` is a 29-page scan with no
  text layer: `pdftotext` returned 29 bytes and the parser silently saw
  nothing, dropping the whole September 2021 review. Its Nifty 500 side turned
  out to be superseded (the 15 September release restates it with Gillette's
  exclusion dropped, which is why the Nifty 500 chain still validated), but
  its Nifty 100 changes existed nowhere else. Read off the rendered pages and
  recorded in `lib/scanned_releases.py`. `lib/extract_text.py` now fails
  loudly on an empty extraction instead of writing it and moving on.
- **Nifty 100 = Nifty 50 + Nifty Next 50.** That release announces the Nifty
  100 review only as a *Nifty Next 50* section. Five companies (Abbott India,
  Alkem, MRF, Petronet LNG, United Breweries) looked like missing exclusions
  until that structure was recognised.
- **Per-index revocations and substitutions.** The March 2024 notice revoked
  IREDA's LargeMidcap 250 inclusion and put **BSE Ltd. in its place**; the
  September 2024 notice revoked Central Bank of India's inclusion. Missing
  either leaves the index one short.
- **Older NSE spellings.** These sheets reach back to 1996 and use names the
  Nifty 500 export never had — Hero Honda Motors, Maruti Udyog, Videsh Sanchar
  Nigam, Gas Authority of India. Event names are now canonicalised up front
  rather than resolved by trying both lookup directions at each step.

## A correction the factsheet caught

The March 2022 check found a real error in the Nifty 500 file: Burger King
India was carried under `BURGERKING`, the ticker it was *included* under,
after it renamed to Restaurant Brands Asia and moved to `RBA` — which is the
symbol its price file is actually keyed on, and which we already hold. A spell
now takes the symbol from its **exclusion** (the later vintage) rather than
its inclusion.

This is exactly the kind of error an endpoint-only test cannot see, since the
company had already left the index by today.

## Not done deliberately

`data/static/nse500_membership.csv` is untouched. Adopting real history there
would change every published backtest number — the same class of change as
the retro-applied corporate actions logged in `om25_published_numbers_drift`.
That is a founder decision and is listed as open in TASKS.md.
