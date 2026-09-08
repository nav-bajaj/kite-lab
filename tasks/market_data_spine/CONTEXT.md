# What the `index_reconstruction` branch established

Everything below was produced on this branch on 2026-09-08 and is the input to
the work planned in `PLAN.md`. Written down because most of it was discovered
rather than designed, and it would be expensive to rediscover.

Branch topology: `index_reconstruction` = `email_channel` + 5 commits. It is
39 commits behind `beta_gtm_mvp` (the live prod branch) and touches nothing
production reads. Nothing here has been merged.

---

## 1. Point-in-time index membership, four indices

Commits `87ec474`, `d4e239f`, `925d22e`. Task folder `tasks/index_reconstruction/`.

`data/static/*_membership.csv` had `effective_from = 1900-01-01` for every
constituent, so every backtest ran today's index membership backwards over the
past — survivorship bias in its purest form. That is now reconstructed from
NSE's own record.

| Index | Span | Events | Matches today | Matches Mar-2022 factsheet |
|---|---|---|---|---|
| Nifty 500 | 1998-08 → | 3,199 | 500/500 exact | 501/501 exact |
| Nifty 50 | 1996-09 → | 222 | 50/50 exact | 50, 49 resolved |
| Nifty 100 | 2003-03 → | 459 | 100/100 exact | 100, 99 resolved |
| Nifty LargeMidcap 250 | 2005-09 → | 1,049 | 250/250 exact | 250, 247 resolved |

Sources: NSE's `IndexInclExcl` workbook (1996-2020, company names only) joined
at 2020-09 to 39 press-release PDFs (2020-2026, names **and** symbols — that
join is what maps historical names onto tradeable tickers). NSE's March 2022
factsheets are an independent checkpoint neither source feeds.

Only the Nifty 500 sheet has a seed. The other three start mid-stream, so their
membership at the first event was derived by un-applying every event backwards
from today's list; each derived seed lands exactly on the index size.

**Things that will bite again:**
- NSE logs an exclusion under a company's name *at exit* and the inclusion under
  its name *at entry*. Unjoined, each rename leaks a phantom member. 62 encoded.
- NSE sometimes **revokes** an announced change before it takes effect, and may
  substitute a different stock (BSE Ltd. replaced IREDA in LargeMidcap 250).
- `pdftotext` returns an EMPTY dump for a scanned release and the parser then
  silently sees nothing. `ind_prs23082021.pdf` (29 bytes from 2.5 MB) dropped a
  whole review. Extraction now fails loudly.
- Nifty 100 = Nifty 50 + Nifty Next 50, so some releases announce the Nifty 100
  review **only** as a Next 50 section.
- Index size is a fixed invariant and therefore the strongest check available.
  Legitimate exceptions: a second share class (Tata Motors DVR, 2016-2024) and
  zero-price demerger placeholders (`DUMMYHEG`).

## 2. Price backfill for ex-members

Commit `7a0e21f`.

357 symbols fetched: **316 from Kite** (still listed, back to 2010) and **41
from GDF** (delisted or BSE-only). GDF serves delisted history that Kite
structurally cannot — Kite's historical API needs an instrument token, which
only live instruments have.

Result: symbols-with-prices now equals symbols-identified at every measured
date. From 2020 all four indices support a fully survivorship-free
point-in-time universe; from 2016 the Nifty 50 and Nifty 100 do. What binds
earlier is name→symbol resolution for old delistings, not price history.

Written to `nse500_data_backfill/` and `nse500_data_backfill_gdf/`, both
gitignored. **`nse500_data/` was not touched.**

16 symbols returned nothing from either feed (pre-2010 delistings, some REITs).

## 3. The price panel is not what anyone assumed

Commit `6fb6a5f`. Reproduce with
`tasks/index_reconstruction/lib/probe_adjustment.py`.

Comparing the STORED panel against a FRESH Kite fetch of the same dates:

| Symbol | fresh ÷ stored | days differing |
|---|---|---|
| ONGC | 0.9770 → 1.0000 | 510 / 668 |
| INFY | 0.9788 → 1.0000 | 591 / 668 |
| ITC | 0.9535 → 0.9735 → 1.0000 | 576 / 668 |
| COALINDIA | 1.0000 | 1 / 668 |

- **Kite's API back-adjusts history for dividends.** A fresh pull is a
  total-return series. **Refetching is not idempotent.** `adjusted_price_series`
  frames this as an announced flip to a fully adjusted series from 2011; the
  fresh-vs-stored numbers above suggest it is already affecting fresh pulls,
  which makes that task's Phase 0 freeze more urgent, not less.
- **`nse500_data` is effectively RAW.** Rows are written once and never
  re-adjusted.
- **GDF is also raw**, so it agrees with the stored panel almost everywhere.
  The two feeds were never really in conflict.
- **The panel is inconsistent with itself.** `history_utils` sets
  `lookback_days = 15` and overwrites the last 15 days every run. When a large
  dividend goes ex, that refetch writes ADJUSTED values over the raw
  pre-ex-date rows inside the window — leaving a short adjusted band inside a
  raw series, with an artificial jump at each edge.
- `data/corporate_actions.json` holds **one** row. Dividends are not modelled
  at all.
- Isolated bad prints exist in the stored panel (INFY 2026-05-27,
  CASTROLIND July 2026), found by cross-checking against GDF.

## 4. What is already immutable, and what is not

Reproduce with `lib/audit_immutability.py`.

Each portfolio run stores a fully recomputed history, so drift is directly
testable. Bisecting every stored run against the latest:

| Portfolio | history stable from | what last moved it |
|---|---|---|
| L6 v2 | 2026-05-14 (first run) | — |
| COMBO | 2026-05-14 (first run) | — |
| OM25 v3 | 2026-06-06 | `aa963eb` trailing stop silently disabled when 200-DMA is NaN |
| TL25 v3 | 2026-06-06 | same fix, shared `_clean_engine` |

That fix added 40 trades to OM25's history and 41 to TL25's — a genuine bug
fix that changed the past.

**The July 2026 universe-membership work did NOT rewrite history.** Trades
before 2026-07-13 are byte-identical across all four portfolios when run in
July versus August. The grandfather rule and candidate mask did their job.

Since those lock dates there have been **5 restatements**, all in L6 and COMBO,
each touching exactly one trade-date, 4-12 days before the run:

```
l6_v2   run 2026-07-21 restated 2026-07-17   (4 days)
l6_v2   run 2026-08-18 restated 2026-08-14   (4 days)
l6_v2   run 2026-08-19 restated 2026-08-14   (5 days)
combo   run 2026-07-10 restated 2026-06-29  (11 days)
combo   run 2026-07-11 restated 2026-06-29  (12 days)
```

Every one sits inside the 15-day refetch window. **Nothing older than that
window has ever moved.** A worked example: L6's 2026-07-17 ABSLAMC sell was
recorded at 1139.30 and later restated to 1111.45 (−2.44%, dividend-sized),
and the changed proceeds cascaded into four other position sizes.

So the record is already ~95% immutable. The mutable part is the most recent
rebalance, and the cause is understood.

## 4a. Where this meets `tasks/adjusted_price_series/`

That task was opened the same day and carries the founder's methodology call:
the panel is **price-return / ex-dividend** — adjusted for splits, bonus,
rights and demergers, never for cash dividends, because dividends reach the
investor as cash and are not assumed reinvested.

Read together, this branch supplies the evidence and that task supplies the
policy:

- It names the exact mechanism — `history_utils.py:236`
  `drop_duplicates(subset=["date"], keep="last")`, so refetched rows win — and
  identifies two further leaks this branch did not find: the
  `apply_corporate_actions.py` CSV-delete recovery path, and a Railway volume
  reset silently re-fetching the whole panel as total-return.
- It notes `apply_corporate_actions.py` will double-adjust once Kite ships
  splits and bonus itself, and that demergers are *not* on Kite's list, so the
  script narrows rather than disappears.
- This branch adds the measurements: five published rebalances already
  restated, and 510-591 of 668 days differing between a fresh pull and the
  stored panel.

An earlier draft of `DECISIONS.md` here argued for total-return signals. That
contradicted a decision already made and has been corrected — see D-3.

## 5. Method notes worth keeping

- Measure coverage from the EMITTED membership file, not a point-in-time
  replay: a long-tenured member only acquires its symbol on the release that
  finally removes it (J.B. Chemicals sat in the index 1998-2026), so a
  mid-spell replay understates.
- Compare recomputed histories by **per-date hashing**. Row-positional
  comparison breaks when the backtest start date changes; a key-merge
  duplicates when a symbol trades twice in a day. Both produced false results
  here before being caught.
- Fuzzy name matching proposes, it never decides. A permissive matcher mapped
  Corporation Bank onto Indian Bank and Dena Bank onto D B Corp, each at a
  perfect score.
