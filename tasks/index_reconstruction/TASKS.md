# Tasks

## Phase 1 — historical export (1998-2020) 🤖 done

- [x] Parse the `IndexInclExcl` export; normalise three date formats
- [x] Replay forward and check the count holds at 500
- [x] Resolve the 15 unmatched exclusions — all company renames where NSE
      logged the exit under the new name and the entry under the old one
- [x] Identify the residual +1 at 2016-04-01 (76 inclusions vs 75 exclusions)

## Phase 2 — press releases (2020-2026) 🤖 done

- [x] Scrape the full press-release archive (1,204 releases on one page)
- [x] Filter to equity constituent changes; download 127 PDFs
- [x] Extract text and write the Nifty 500 section parser
- [x] Handle the four layout variants found: numbered vs lettered section
      headers, upper vs mixed case index names, multiple Nifty 500 sections
      in one release, and company names wrapped over three table lines
- [x] Model revocations — changes NSE announced then cancelled before they
      took effect (risk: silently moves a stock that never moved)
- [x] Recover the two corporate actions that list index names only, with no
      per-index company table (Tata Motors DVR cancellation, HEG demerger)

## Phase 3 — join and validate 🤖 done

- [x] Join at 2020-09-14, cutting the CSV *before* the handoff (it records
      only 1 of the 5 changes the press release lists that day)
- [x] Resolve the 48 cross-era renames against the current constituent list
- [x] Handle the Tata Motors demerger, where the old name is reused by a
      different company (risk: name collision between two live entities)
- [x] Acceptance test through the production `universe_membership` loader

## Phase 4 — emit 🤖 done

- [x] `nse500_events_reconstructed.csv` (3,199 events)
- [x] `nse500_membership_reconstructed.csv` (1,214 windows, repo schema)
- [x] `unresolved_symbols.csv` (635 spells, mostly delisted pre-2020)

## Handed to `tasks/market_data_spine/`

The follow-on work — day-to-day data source, corporate-action system, master
historical file, portfolio re-runs on the dated universe, the immutable ledger
and the standing membership procedure — is planned there. `CONTEXT.md` in that
folder carries the full findings from this branch.

## Open / deferred 👤

- [ ] Founder call: adopt real history in `data/static/nse500_membership.csv`?
      It will move every published backtest number.
- [x] Second-pass symbol resolution via BSE dump rows + rename chasing
      (+103 companies; 2016 coverage 74% -> 79%, 2010 64% -> 72%)
- [x] 👤 GDF key renewed 2026-09-08; confirmed working and confirmed to serve
      DELISTED history, which Kite cannot
- [x] Price backfill done: 316 symbols via Kite, 41 via GDF. Every identified
      symbol across all four indices now has a price file
- [ ] 👤 Decide whether to stitch the backfill into `nse500_data_merged`. The
      GDF series use a different dividend-adjustment convention (see RESULTS)
- [ ] 16 symbols returned no data from either feed (pre-2010 delistings, some
      REITs); listed in `data/price_backfill_targets.csv`
- [ ] Residual 491 companies unresolved, mostly pre-2010 delistings absent
      from every live instrument master. Needs a historical symbol master.
- [x] Same pipeline for Nifty 50 / 100 / LargeMidcap 250 — all three derived
      backwards from today's list, seeds exact, validated on the March 2022
      factsheets with zero extras
- [ ] Nifty Midcap 150 on its own (LargeMidcap 250 minus Nifty 100 gives it
      indirectly; a direct build would need its own sheet, absent from the
      workbook)
- [ ] 3 companies unresolvable to a ticker (HDFC, MINDTREE, ISEC) — merged or
      delisted with no successor to key a price file on
