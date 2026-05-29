# NSE index constituent weights — dated factsheet snapshots

## Layout

```
data/static/index_weights/
├── NIFTY_50/
│   └── 2026-04-30.csv        # factsheet date is the filename
├── NIFTY_BANK/
│   └── 2026-04-30.csv
├── NIFTY_FINANCIAL_SERVICES/
├── NIFTY_IT/
├── NIFTY_MIDCAP_SELECT/
└── NIFTY_NEXT_50/
```

## Source

NSE Indices factsheets — one-page PDF per index, published monthly at
<https://www.niftyindices.com/reports/factsheet>. Each row in the CSV
mirrors the factsheet table exactly:

```
symbol,security_name,industry,close_price,index_mcap_cr,weight_pct
```

The `weight_pct` column is what the index attribution engines consume.
Loaders normalise to sum to 100 on read so partial-precision rounding
in the source doesn't compound downstream.

## Refresh cadence

The factsheets are published monthly on or around month-end. Weights
drift between factsheets as constituents move and shares-outstanding
change. For "today's move attribution" use, the most recent monthly
factsheet is plenty accurate. For historical attribution, we'd need a
dated panel of factsheets per month — out of scope for now.

## When you refresh

1. Download the factsheet PDFs to a working folder
2. Transcribe each into a new `YYYY-MM-DD.csv` under the matching index folder
3. The loader auto-picks the most recent dated file per index
4. Commit the new factsheets alongside the existing ones — never overwrite
   prior dated snapshots; we'll want the trail later for time-series
   weight analysis

## Caveats

- Some indices include placeholder symbols during corporate-action events
  (e.g., "DUMMYVEDL1-4" in NIFTY Next 50 after Vedanta demerger). These
  do not have price data and should be filtered by downstream consumers.
- Symbol changes (e.g., TATAMOTORS → TMPV after demerger) — the factsheet
  carries the current symbol, but our price panel may not. Cross-check
  against `nse500_data_merged/` when adding a new index.
