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
