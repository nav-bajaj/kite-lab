# Adjusted price series — holding a price-return panel against a total-return feed

## Why this task exists

Kite is moving historical candles to a **fully adjusted series starting
2011**, adjusting for cash dividends, stock splits, bonus issues and
rights issues.

The founder's methodology call (2026-09-08): **we do not want dividend
adjustment.** Dividends flow to the investor as cash; we do not assume
reinvestment. Marketworks research and published track records are
**price-return, ex-dividend**, and are to be labelled as such.

Three of the four adjustments Kite is adding are ones we *want* — splits,
bonus and rights are share-count events, not cash flows, and a series
that ignores them is simply wrong. The fourth, cash dividends, is one we
must actively **keep out**.

So this is not a migration onto a new feed. It is the opposite: the
provider is about to start shipping something we have to hold the line
against. The panel's price-return property stops being a free consequence
of the feed and becomes an invariant we own and must enforce.

## Current state (verified 2026-09-08)

| Panel | Range | Provenance | Adjustment |
|---|---|---|---|
| `nse500_data/` | 2020-01-01 → present | Kite | split + bonus, **no dividends** |
| `nse500_data_merged/` | 2009-03 → present | GDF splice below 2020 + Kite above | split + bonus, no dividends |
| `nse500_data_hourly/` | trailing 90d | Kite | n/a at this horizon |

- `scripts/update_all_portfolios.py:76-92` runs all four production
  portfolios against `nse500_data` — the 2020+ panel. The
  `nse500_data_merged` default in `run_om25_v3_portfolio.py:139` applies
  only to standalone invocations.
- `scripts/history_utils.py:186-241` is **already append-only for
  history**: it reads the existing CSV, sets `fetch_start` past the last
  stored row, concatenates and de-duplicates. History is not re-downloaded
  on a normal day.

That second point is the whole opportunity. Our stored history is
price-return today, and stays price-return for as long as nothing
re-downloads it. Kite's adjustment only ever rewrites candles *before* an
ex-date; the candle for a new trading day arrives at the price that
actually traded. **Append-only is the ex-dividend policy**, implemented.

## The three leaks

The append-only property is real but not airtight. Three paths pull
history back down from the provider, and after the flip each one returns
dividend-adjusted prices.

**1. The 15-day trailing re-fetch — `scripts/history_utils.py:270`**

```python
lookback_days = 15 if cfg["interval"] == "day" else 0
```

Every daily run re-fetches the trailing 15 days and merges with
`drop_duplicates(subset=["date"], keep="last")` — the fetched rows win.
After the flip, when a stock goes ex-dividend, those 15 rows come back
dividend-adjusted while row 16 and older stay raw. The result is a band
of adjusted prices grafted onto unadjusted history with an artificial
step at the boundary. Per symbol, per dividend event, silently. Indian
large caps mostly pay once or twice a year, so this accumulates into a
speckled panel over a single cycle. **This is the one that bites first
and is hardest to spot after the fact.**

**2. The CSV-delete recovery path — `scripts/apply_corporate_actions.py:120,138`**

`os.remove(csv_path)` deletes a price file when it detects an
unrecoverable mixed adjustment state, deliberately so the next fetch
downloads clean raw data. Post-flip that re-fetch is not raw any more.
The recovery mechanism becomes a dividend-adjustment injector, one symbol
at a time.

**3. Volume loss**

The panel lives on a Railway persistent volume. Any volume reset, fresh
environment, or first-run bootstrap triggers a full re-fetch — and the
entire panel silently becomes total-return with no error and no visible
change in shape. Right now the only thing protecting the price-return
property of six years of history is that the disk has not been wiped.

## Second-order consequence: `apply_corporate_actions.py` double-adjusts

The script exists to patch corporate actions Kite did *not* apply. Kite's
new list covers splits, bonus and rights — so applying our factors on top
of Kite's own becomes a double adjustment.

Note the asymmetry: **demergers are not on Kite's list.** The only event
currently in `data/corporate_actions.json` is the VEDL 2026-04-30
demerger. So this script must not be deleted; its scope narrows to
demergers and anything else the provider does not handle, and the
threshold heuristics it uses to detect "raw" rows need re-basing against a
feed that now arrives partly adjusted.

## Scope boundary

In scope: the adjustment convention for `nse500_data`, its enforcement,
and the documentation of the ex-dividend stance.

Out of scope for now: the 2011-2020 backfill (see open decision below),
indices and cross-asset panels, options data, and any re-baselining of
published portfolio numbers — the ex-dividend stance means the published
curve does **not** move, which is a significant benefit of this call.

## Open decision — the 2011 depth

The founder chose (2026-09-08) to keep the GDF splice below 2011 rather
than truncate. That answer was given before the ex-dividend stance was
settled, and the two interact:

- Our price-return panel starts **2020-01-01**.
- Production backtests are configured to start 2016-01-01
  (`run_om25_v3_portfolio.py:153`) but can only run from where data
  exists.
- Pulling Kite's 2011-2020 segment would deepen the panel by nine years —
  but that segment arrives **dividend-adjusted**, which is exactly what
  we have decided to exclude.

Three ways out, none of which should be picked by inference:

(a) **Do not pull it.** Panel stays 2020+. Simple, consistent, no seam.
    Costs the 2016-2020 depth production is nominally configured for.
(b) **Pull and de-adjust.** Reverse Kite's dividend factors using a
    dividend event table (ex-date + dividend per share per symbol). We
    have `data_pipeline/eodhd_client.py` and `gdf_client.py` as candidate
    sources. Gives a clean price-return series to 2011; costs a dividend
    feed we do not currently have and must validate.
(c) **Pull and label.** Take the segment as-is and mark 2011-2020 as
    total-return in the manifest. Cheapest, but puts a methodology seam
    inside the backtest window, which undercuts the point of the
    ex-dividend stance.

Recommendation: (a) now, (b) as a separate task if the depth is wanted.
Flagged for the founder — not decided.

## What "done" looks like

1. The pre-flip panel is frozen and reproducible.
2. The three leaks are sealed; no code path can silently pull
   dividend-adjusted history into the panel.
3. `docs/price_data_contract.md` states the convention as the single
   authority, and CLAUDE.md carries it as an invariant.
4. A test fails, loudly, if frozen history ever moves.
5. The daily pipeline aborts before portfolios run if the panel's
   adjustment state does not match its manifest.
