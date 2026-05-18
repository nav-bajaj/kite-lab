# GDF Full Backfill — Plan

**Goal:** While we have working GDF API access, fetch the deepest
possible historical price history for NSE 500 stocks + key indices,
and archive the result somewhere it'll survive losing GDF access in
the future.

**Why now:** GDF is a paid subscription. The current historical
backfill we hold (``~/Documents/stock_data/nse500_data_historical/``,
382 stocks, 2009-2019) is what the May 2026 OOS retune evidence in
``tasks/oos_retune_2026/RESULTS.md`` was computed against. Any future
retune attempt that wants more recent IS data, or earlier history,
will need GDF. If the subscription lapses or the vendor disappears,
that capability disappears with it. One thorough fetch right now =
permanent capability later.

**Status:** PLANNING. No execution started.

---

## What we already have

| Component | Where | Status |
|---|---|---|
| GDF websocket client | ``data_pipeline/gdf_client.py`` | working — auth + GetHistory tested |
| API-limits probe | ``scripts/_gdf_limits_probe.py`` | exploratory; results need re-running |
| Index stitching (GDF + Kite) | ``scripts/stitch_gdf_indices.py`` | working pattern; can mirror for stocks |
| Stock stitching (GDF 2009-19 + Kite 2020+) | ``scripts/stitch_gdf_kite.py`` (referenced in stitch_gdf_indices) | working |
| Existing 2009-2019 historical | ``~/Documents/stock_data/nse500_data_historical/`` | 382 files, 35 MB |
| Existing 2009-2019 indices historical | ``~/Documents/stock_data/indices_data_historical/`` | unknown count, need to inspect |
| GDF API key | ``.env`` (gitignored) | active subscription |

---

## Known GDF constraints (to verify in Phase A)

1. **Single-session API key.** Overlapping connections get
   "Access Denied. Key already in use by other session." Always
   close cleanly. Implication: no easy parallelism — must serialize.
2. **Per-request bar cap.** Probe is investigating. If yes, requests
   must be year-chunked or month-chunked to span 30+ years.
3. **Per-session symbol cap.** Possibly 100. If yes, fetcher must
   close + reopen the connection every ~100 symbols.
4. **2024-25 coverage gap.** Probe is investigating. Could mean
   GDF data ends in late 2023, in which case we stitch with Kite
   (which goes 2020+).
5. **Earliest available date varies by symbol.** A 2024 IPO won't
   have 2009 data; an old name like RELIANCE goes back to the
   1990s. The fetch must request a wide window and accept whatever
   comes back.

---

## Proposed phases

### Phase A — Audit & calibrate (1-2 hours)

A.0 Branch off main: ``git checkout -b gdf-full-backfill``

A.1 Re-run ``scripts/_gdf_limits_probe.py`` against the live API and
document the answers to the four constraints above. Append findings
to ``tasks/gdf_full_backfill/PROBE_RESULTS.md``.

A.2 Compile the target universe:
- **Stocks:** current NSE 500 (``data/static/nse500_universe.csv``)
  + the historical 382 already in
  ``~/Documents/stock_data/nse500_data_historical/`` so we don't
  drop names already gone from the index. Union ~ 600 symbols.
- **Indices:** Nifty 50, Nifty 100, Nifty 250, Nifty 500, Nifty
  Bank, Nifty IT, Nifty Auto, Nifty Pharma, Nifty FMCG, Nifty
  Metal, Nifty Realty, Nifty Energy, Nifty Smallcap 100, Nifty
  Midcap 100. Inventory current ``indices_data_historical/`` and
  extend.

A.3 Decide the date window. Default: 1995-01-01 → today.
GDF will return less for symbols that listed later; that's fine.

### Phase B — Design fetcher (2-3 hours)

B.1 Write ``scripts/gdf_full_backfill.py``:
- Reads target universe from a CSV
- Per-symbol loop: request 1995-01-01 → today
- Year-chunks the request if Phase A confirmed a per-request cap
- Closes/reopens the websocket session every N symbols (N from
  Phase A; conservatively 50)
- Writes ``<output>/<symbol>_day.csv`` matching the existing
  ``nse500_data_historical/`` schema
- **Checkpoint file** ``<output>/.progress.json`` so a crashed run
  resumes from the last completed symbol instead of re-fetching
- **Idempotent**: skipping symbols whose output CSV is already
  populated with bars ending within 7 days of "today"
- Logs to ``<output>/.fetch.log``

B.2 Write a small validator that reports, per output CSV:
- Earliest date present
- Latest date present
- Gap count (date holes inside the present range)
- Total bar count

B.3 Pick output location:
- Local: ``~/Documents/stock_data/nse500_data_gdf_full/`` (gitignored)
- After fetch completes, package as a tarball and upload via
  the Phase 2.5.6 plumbing:
  - Drive: via ``scripts/upload_to_gdrive.py`` (snapshot
    pattern will pick up the new folder)
  - Railway volume: via ``scripts/upload_price_data.py
    --target nse500_data_gdf_full`` (requires adding that name
    to the allowed-targets list)

### Phase C — Execute (multi-hour, mostly unattended)

Wall-clock estimate:
- 600 symbols × ~1s per fetch × N years / chunks
- If 5-year chunks and 30 years history: 600 × 6 chunks ≈ 3600
  requests × 1s = ~1 hour at no rate-limit
- Add safety margin for reconnects, transient errors, retries
- Realistic: **3-6 hours of unattended wall-clock**

Run from the Mac (laptop must stay on, but no user input needed
after launch). Checkpoint file means an interrupted run is
recoverable.

### Phase D — Package & archive (30 min)

D.1 Run validator across all output CSVs; sanity-check the
coverage table.

D.2 Tarball: ``nse500_data_gdf_full_<YYYYMMDD>.tar.gz``.

D.3 Upload to Drive via ``upload_to_gdrive.py`` (will land in
``kite-lab-backups/nse500_data_gdf_full_snapshots/`` per the
Phase 2.5.4 pattern).

D.4 Upload to Railway volume via ``upload_price_data.py`` — once
the target whitelist is updated to include this new name. Optional
but means the data is also available to backtest scripts running
in Railway.

D.5 Update ``tasks/pipeline_improvements/CRITICAL_DATA.md`` —
move ``nse500_data_historical`` from HIGH-risk to LOW-risk, and
add ``nse500_data_gdf_full`` as a new irreplaceable asset.

D.6 Commit the **metadata** to git (universe used, date range
fetched, validator output, fetch logs). Do NOT commit the price
data itself — it stays gitignored.

---

## Open questions for the operator

1. **Universe scope:** current NSE 500 only, or also historical
   constituents that have dropped out of the index since 2009?
   The latter avoids survivorship bias in future retunes.
2. **Periodicity:** daily only, or also hourly / minute? Hourly
   for 30 years × 600 symbols is *much* larger.
3. **Coverage end:** stop where GDF stops (which Phase A will
   determine), or stitch with Kite immediately? The existing
   ``stitch_gdf_kite.py`` pattern handles the latter cleanly.
4. **Where to host the data long-term?**
   - Mac-local only (single-device risk, but cheap)
   - Mac + Drive cloud (recommended; matches Phase 2.5.4 pattern)
   - Mac + Drive + Railway volume (lets backtests run against this
     data from the production env)
5. **When to run Phase C?** This blocks the Mac for several hours.

---

## Out of scope (deliberately)

- Intraday/minute data (separate, much larger backfill)
- Options / futures (different GDF endpoints)
- US equities (we have a small US backfill from the L6/OM25 US
  retune work in ``tasks/l6_us_tune_2026/`` etc. — separate effort)
- Real-time / live GDF streaming (we use Zerodha for live; GDF
  is purely a historical-data source for us)
