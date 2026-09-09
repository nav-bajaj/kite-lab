# Decisions

Recorded here because each one gets much more expensive to change after SEBI
registration, when the published numbers stop being internal.

---

## D-1 — Kite is the day-to-day source of record. GDF is the supplement.

**Decision.** Kite is the primary feed for daily prices. GDF is used for what
Kite structurally cannot serve, and as an independent cross-check. Every stored
row records which feed it came from.

**Why Kite is primary.** It is the execution venue, so its prices are the ones
orders actually fill against. The token flow, rate limiting and retry logic
already exist. The entire live panel and the whole published record are built
on it — changing the primary feed would invalidate the record for no gain.

**Why GDF stays.** Kite's historical API resolves an instrument token, which
only exists for live instruments, so **delisted scrips are invisible to it**.
Any survivorship-free universe needs the companies that died, and GDF serves
them to their delisting date (Allahabad Bank to its 2020 merger, Tata Coffee to
2024, the Tata Motors DVR line to its 2024 cancellation). GDF also floors at
2009-01-01 against Kite's 2010, and it independently surfaced bad prints in the
Kite panel. It earns its place as the second opinion, not the default.

**What this rules out.** Using GDF as the primary feed, and silently mixing the
two in one series. A row's source is part of its identity.

## D-2 — Store raw, adjust on read.

**Decision.** The price store holds prices **as fetched**, append-only. Rows are
never rewritten. Corporate actions live in a separate dated event table. An
adjusted series is a derived view, computed from raw × factors, with an
as-of date.

**Why.** This is the only model that satisfies both requirements at once:

- *"Use the data we have that day and don't change it afterwards"* — raw rows
  are immutable, so a decision made on day D can always be reproduced.
- *A clean series for research* — the adjusted view can be restated freely as
  corporate actions land, because it is derived rather than stored.

Today the panel does neither: it is raw except for 15-day bands of adjusted
prices cut into it by the refetch, which is the one option with no defence.

**Consequence.** `lookback_days = 15` must go. A refetch may only correct a row
that was provisional, never re-adjust a settled one. A refetch that changes
many old rows by a constant ratio is an adjustment, not a correction, and is
mechanically detectable — so it can be rejected rather than trusted.

## D-3 — Price-return, ex-dividend. (Founder's call, already made.)

**Decision — not mine.** The panel is price-return / ex-dividend: adjusted for
splits, bonus, rights and demergers, **not** for cash dividends. Made by the
founder on 2026-09-08 and written up in `tasks/adjusted_price_series/`.

**Why.** Dividends reach the investor as cash and are not assumed reinvested,
so a price-return curve is the honest, conservative claim — realised investor
returns are *higher* than reported by the dividend yield. That is the right
footing for a SEBI-registered product, and it means the published curve does
not move.

**Correcting an earlier recommendation in this folder.** An earlier draft of
this file argued for total-return signals on the grounds that a price-return
series penalises dividend payers over a 12-month lookback. That bias is real
but it is a ranking effect measured in a percent or two a year, and it is the
wrong trade against restating a published track record and reporting returns an
investor did not receive. The founder's call stands; this decision is recorded
here only so the two task folders do not disagree.

**Consequence.** The work is not to adopt an adjusted series but to *hold the
line against one*. Kite is moving its historical candles to a fully adjusted
series from 2011, so the panel's price-return property stops being a free
consequence of the feed and becomes an invariant that has to be enforced. That
enforcement is `tasks/adjusted_price_series/`, not this folder.

## D-4 — The immutable record starts at each strategy's own lock date.

**Decision.** The ledger begins at the date each strategy's recomputed history
last changed, not at a single shared date:

| Portfolio | ledger starts |
|---|---|
| L6 v2 | 2026-05-14 |
| COMBO | 2026-05-14 |
| OM25 v3 | 2026-06-06 |
| TL25 v3 | 2026-06-06 |

**Why not a single date.** OM25 and TL25 had a real behaviour change on
2026-06-06 (the trailing-stop fix, +40 and +41 historical trades). L6 and COMBO
did not, and there is no reason to discard six weeks of their record to force a
shared start. These dates were established empirically by bisecting stored runs,
not from commit dates — the July membership commit touched all four engines
without changing any output.

**A gap to be honest about.** The lock date is when the strategy stopped
changing; the ledger can only record rebalances that were actually run and
stored. For L6 and COMBO those coincide (first stored run 2026-05-14). For
OM25 and TL25 they do not — locked 2026-06-06, but the first stored run after
that is **2026-07-10**, so roughly five weeks have no recorded decision. Those
weeks are reconstructable from the recomputed history, but a reconstruction is
not a contemporaneous record and should not be presented as one.

**Consequence.** Everything before those dates is backtest under an earlier
strategy version and must be labelled as such. Backtested returns cannot be
presented as a live track record after registration anyway.

## D-5 — Nothing published is recomputed.

**Decision.** Published performance is derived from the frozen ledger of
decisions plus actual prices. The engine is never re-run to produce a published
number.

**Why.** The engines recompute full history on every run today, so any input
restatement silently rewrites the past. Five such restatements have already
happened. Freezing the decision separates "what we told clients" from "what our
research series currently says", which is the distinction a regulator cares
about and the only one that survives a data correction.

---

## 2026-09-10 — founder decisions that revise the above

## D-6 — Total return. Kite's adjusted series is the basis. (Reverses D-3.)

**Decision (founder).** Use Kite's fully adjusted history — dividends, splits,
bonus, rights — as the research price basis. The price-return / ex-dividend
stance in D-3 no longer applies to research data.

**Consequences.**
- Published backtest numbers move up by roughly the dividend yield once
  re-based. Client copy that says "ex-dividend" is withdrawn, not amended.
- An ex-date rewrites a symbol's entire prior history. Append-only (D-2) is
  therefore replaced by **versioned snapshots**: each pull is stored under its
  date, and a backtest records the snapshot it read. Reproducibility is per
  snapshot.
- Delisted names Kite cannot serve are brought onto the same basis by
  applying NSE-filed corporate actions to GDF's raw series (Phase 4). Kite's
  formula is measured, not assumed.

## D-7 — Fresh from scratch.

**Decision (founder).** The master store is built by pulling every series
anew. Nothing is copied from `nse500_data`, `nse500_data_merged`, the backfill
directories or the Documents mirrors. Those remain exactly as they are for
production and are used only as a cross-check.

## D-8 — Production is not touched.

**Decision (founder).** New membership files, new price store, new loader.
`data/static/*_membership.csv`, `nse500_data*`, `history_utils.py`,
`apply_corporate_actions.py`, the daily pipeline and everything the dashboard
reads stay as they are. Moving production onto the master store is a later,
separate decision.

## D-9 — Delisting at last traded price.

**Decision (founder).** A position in a stock that delists exits at the last
price the feed served, on that date, with no haircut. The store records
`delisted_on` per symbol; the engine treats it as a forced exit, not a
forward-fill. This is optimistic for bankruptcies and exact for mergers with
cash consideration; it is recorded as the convention and labelled in results.

## D-10 — One program.

**Decision (founder).** `adjusted_price_series` and `corporate_actions_fix`
are absorbed into this folder. Their findings are carried in CONTEXT.md and
TASKS.md; their folders are marked absorbed and left in place for the record.

## D-1, revised — Kite is the source for history too.

D-1 made Kite the day-to-day source and GDF the supplement. Verified
2026-09-10: Kite serves day candles from 2000-01-03 for live instruments, so
it is also the history source. GDF's role narrows to the 37 symbols with no
Kite instrument. D-2's "store raw" survives as the reconciliation layer
(bhavcopy closes × CA factors must reproduce Kite), not as the basis.

## D-11 — The database begins 2006-01-01. (Founder, 2026-09-10.)

**Decision.** Twenty years, 2006 to today, for all four indices. 2005 is
fetched as run-in so a 252-day lookback is fully populated on the first
signal date of 2006. Nothing before 2005 is fetched or promised.

**Why 2006 and not earlier.** Depth probes (CONTEXT.md §6) showed prices
reach 1995 (bhavcopy) and 2000 (Kite adjusted), but NSE's corporate-action
filings are thin before 2005 — 70-218 rows a year against 829 in 2005 and
~2,200 today. A delisted name's series can only be adjusted from that
table, so before 2005 a missed bonus or split becomes a false crash that a
momentum rank would trade. 2006 keeps the whole panel inside the dense era.

**Consequence for sources.** GDF floors at 2009, so for 2005-2009 the
delisted names must come from the bhavcopy anyway. The bhavcopy therefore
becomes the price source for every symbol Kite cannot serve, across the
whole span, adjusted by the CA table; GDF is retained only as an
independent second opinion on those series. D-1 (revised) stands for live
names: Kite adjusted, from 2000, is the basis.

**Consequence for gates.** Coverage is measured from 2006, not 2016:
≥ 95% of the index size resolved and traded on every event date from
2006-01-01, ≥ 98% from 2016-01-01. The retune's in-sample window can then
be 2006-2015 with 2016-2026 out of sample.

## D-6, note added 2026-09-10 — the mechanism is under revision

Measured the same day: Kite dividend-adjusts only from about late 2023
(RESULTS.md, Phase 3). The decision's intent — a total-return basis — is
unaffected; its mechanism — Kite's series as the basis — is not achievable
for history. Proposed replacement: bhavcopy raw × NSE-filed factors,
applied on read, for every symbol; Kite becomes the cross-check. Whether
the default view is total-return or price-return is the founder's call,
pending. Nothing published derives from either yet.
