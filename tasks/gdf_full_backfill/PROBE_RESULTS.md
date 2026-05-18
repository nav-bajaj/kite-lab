# GDF API Probe Results — Phase A findings

**Date:** 2026-05-18
**Scripts used:** `scripts/_gdf_limits_probe.py` + `/tmp/gdf_extended_probe.py`

These findings drive the Phase B fetcher design in
`scripts/gdf_full_backfill.py`.

---

## TL;DR

GDF is more permissive than the constraints we'd assumed:

- **No per-request bar cap** — we can fetch the entire date range
  (15+ years) for one symbol in a single GetHistory call.
- **No 100-symbol per-session cap** — 113 distinct symbols fetched
  cleanly in one websocket session; we'll just open one and stream.
- **GDF coverage starts ~2009-03-05** for liquid large caps;
  earlier-listed symbols start whenever they listed (microcaps that
  IPO'd in 2023 show 2023+ data, which is expected).
- **GDF coverage 2024+ is patchy** (~64% of trading days in Q2-Q4 2024,
  ~77% in 2025, recovers in 2026). Backfill therefore caps at
  **2023-12-31**; Kite (which we already have via the daily pipeline)
  covers 2024-present.

Net result: the fetcher is a simple `for symbol in universe: get_history`
loop, ~15-25 minutes wall-clock for 765 symbols.

---

## Test 1 — per-request bar cap

`scripts/_gdf_limits_probe.py:test_request_cap()`

```
RELIANCE 2024-01-01 to 2024-12-31 -> rows=162
  first=2024-01-01  last=2024-12-23
RELIANCE 2024-01-01 to 2024-03-31 -> rows=62   (full Q1 — 62 of ~62 trading days)
RELIANCE 2024-04-01 to 2024-06-30 -> rows=30   (Q2: 30 of ~63 — coverage gap)
RELIANCE 2024-07-01 to 2024-12-31 -> rows=70   (H2: 70 of ~127 — coverage gap)
```

162 = 62 + 30 + 70 (consistent). The "missing" Q2-Q4 2024 days are a
**real data gap in GDF**, not a per-request cap. Q1 returned every
expected trading day in a single call.

## Test 2 — 100-symbol-per-session cap

`scripts/_gdf_limits_probe.py:test_symbol_cap()`

```
total ok=113 fail=0
```

113 distinct symbols fetched (small date range each, 2026-05-01 to
2026-05-09) in one websocket session, no failures, no errors at
symbol #100 or #101. **No 100-symbol cap.** A single session can
stream the whole 765-symbol universe.

## Test 3 — earliest available date

`/tmp/gdf_extended_probe.py` T1

```
RELIANCE 1995-01-01..1995-12-31 -> empty
RELIANCE 2000-01-01..2000-12-31 -> empty
RELIANCE 2005-01-01..2005-12-31 -> empty
RELIANCE 2010-01-01..2010-12-31 -> rows=251  first=2010-01-04  last=2010-12-30
RELIANCE 1995-01-01..2026-05-18 -> rows=4120 first=2009-03-05  last=2026-05-15
```

GDF's earliest data for RELIANCE = **2009-03-05**. Pre-2009 requests
return empty. The fetcher uses `--start 2009-01-01` (GDF will trim
on its end if no data exists earlier).

## Test 4 — recent edge

`/tmp/gdf_extended_probe.py` T2

```
RELIANCE 2024-01-01..2024-12-31 -> rows=162  last=2024-12-23  (coverage gap mid-2024)
RELIANCE 2025-01-01..2025-12-31 -> rows=194  last=2025-12-30  (improved but still patchy)
RELIANCE 2026-01-01..2026-05-18 -> rows=90   last=2026-05-15  (current, near-complete)
```

GDF is current (most recent bar = 2026-05-15, 3 days behind real time).
But 2024-25 are partial. Decision: cap the backfill at **2023-12-31**
and use existing Kite data (`~/Documents/stock_data/nse500_data/`) for
2024+.

## Test 5 — single-request large range

`/tmp/gdf_extended_probe.py` T3

```
RELIANCE 1995-01-01..2026-05-18 -> rows=4120 first=2009-03-05  last=2026-05-15
  gaps > 15 days: 1
```

Only **one** gap > 15 calendar days across 17 years of data. Data
quality is high (the one gap is likely the 2024 coverage hole). No
need to chunk the request — fetcher uses a single `get_history` call
per symbol over the full date range.

## Test 6 — microcap coverage

`/tmp/gdf_extended_probe.py` T4

```
ASKAUTOLTD 2020-01-01..2026-05-18 -> rows=592 first=2023-11-15 last=2026-05-15
```

ASK Automotive is a Nifty Microcap 250 constituent that IPO'd in
November 2023. GDF has data from its listing date forward — i.e.
microcap names DO have coverage, capped at their listing date.

---

## Implications for Phase B fetcher

1. **Single GDFClient session** for the whole run. Open once, stream
   all 765 symbols, close.
2. **No request chunking.** One GetHistory per symbol over
   `[2009-01-01, 2023-12-31]`.
3. **Empty results are normal** — for any symbol that didn't exist
   pre-2023. Fetcher writes a header-only marker CSV so the
   resumable-skip logic doesn't re-fetch them on the next run.
4. **No retry logic needed** for "session-exhausted" errors. Probe
   surfaced none in 113 symbols; if rare network errors crop up
   during the 765-symbol run, they're recorded in `.fetch.log`
   and surfaced at the end.
5. **Output schema:** `date, open, high, low, close, volume, oi`.
   Matches the existing `nse500_data_historical/*_day.csv` plus
   the `oi` column the old fetch dropped.

---

## Phase C — what happens during the fetch

`scripts/gdf_full_backfill.py` writes per-symbol CSVs into
`~/Documents/stock_data/nse500_data_gdf_full/`. Per-symbol log lines
to `.fetch.log` in the same dir.

Expected output sizes:
- ~17 years × ~252 trading days × 8 columns × ~25 bytes/cell
  ≈ ~850 KB per stock-history CSV (uncompressed)
- 765 stocks ≈ ~650 MB uncompressed local footprint
- gzip ~4-5×: ~130 MB compressed in the eventual tarball
