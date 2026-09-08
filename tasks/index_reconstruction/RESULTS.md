# Results

Status: reconstruction complete and validated. Not yet adopted into the
production universe — see the open founder decision at the bottom.

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
| `data/pr_text/` | 128 | extracted release text (PDFs are gitignored, refetchable) |

Rerun with `python3 lib/fetch_press_releases.py && python3 lib/emit_membership.py`,
check with `python3 lib/validate.py`.

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

## The price backfill is mostly a Kite job, not a GDF one

`data/price_backfill_targets.csv` lists the 194 symbols that are now
identified but have no daily file on disk. The useful surprise:

| | Count |
|---|---|
| still live on NSE — Kite can fetch history directly | 186 |
| BSE-listed only | 1 |
| genuinely delisted (BURGERKING, TATACOFFEE, PEL, INFIBEAM, MAHINDCIE, TATASTLLP, GLS) | 7 |

So 96% of the backfill needs no special vendor. Fetching those 186 would take
2020 coverage from 385/501 to ~432/501 and 2016 from 311 to ~394.

**GDF could not be tested: the API key in `.env` has expired** — the feed
answers `AuthenticateResult: Key Expired.` Nothing was disrupted (the session
never opened, and the key is single-session so a live probe would have been
the real risk). Whether GDF serves history for delisted scrips is therefore
still unverified; it only matters for those 7 symbols plus whatever remains
of the 491 companies that no live instrument master carries — overwhelmingly
pre-2010 delistings.

## Not done deliberately

`data/static/nse500_membership.csv` is untouched. Adopting real history there
would change every published backtest number — the same class of change as
the retro-applied corporate actions logged in `om25_published_numbers_drift`.
That is a founder decision and is listed as open in TASKS.md.
