# Market data spine — one program

## Why

The survivorship-free tests run on 2026-09-09 (CONTEXT.md §7) put the
published numbers where they actually stand: L6 v2 at ~18% CAGR from 2018
rather than ~50%, OM25 v3 at ~30% rather than ~46%. Every strategy was tuned
and every published figure computed on a universe that could not lose a
member, with a price panel that mixes three adjustment conventions and has
been restated in production five times. Nothing can be retuned until the data
underneath it is right, and the pre-registration window is the only time the
foundations can move without a client noticing.

This folder is the single program for that. It absorbs
`tasks/adjusted_price_series/` and `tasks/corporate_actions_fix/`; their
findings are carried here and their folders marked absorbed. Founder
decisions taken 2026-09-10 are in DECISIONS.md D-6 to D-10 and override
anything earlier that conflicts.

## Outcome

A master stock database, built fresh, that a backtest can be pointed at and
trusted:

1. **Symbol master** — every company that was ever in the Nifty 50 / 100 /
   LargeMidcap 250 / 500, keyed by ISIN, with its symbol history, so a 2014
   delisting resolves to a ticker as reliably as a 2026 member.
2. **Point-in-time membership** for the four indices, in the loader's schema,
   as NEW files. Production `data/static/*_membership.csv` is not touched.
3. **Prices, pulled fresh**: Kite's adjusted series from 2000 for everything
   Kite lists (988 of 1,025 symbols), GDF from 2009 for the 37 delisted, every
   row source-tagged. **2006-2026, twenty years**, for all four indices (D-11); 2005 fetched as lookback run-in.
4. **A corporate-actions table** from NSE's own filings, 2005 onward, used to
   bring the GDF series onto Kite's convention, to cross-check Kite, and to
   keep the store correct going forward.
5. **Cleaned**: one calendar, no phantom rows, bad prints quarantined,
   delisted names ended at last traded price, every gap named.
6. **Re-baselined**: all four production portfolios run at their CURRENT
   parameters on this data, with every difference against today's published
   number attributed to universe, price basis or corporate action.

Then, and only then, OM25 gets retuned — as a separate task.

## What changed on 2026-09-10 (founder decisions)

- **Total return, not price return.** Kite's adjusted series is the basis.
  This reverses D-3. Consequence: dividends are in the curve, published
  numbers move up by roughly the dividend yield, and an ex-date rewrites a
  symbol's whole prior history by design — so the store is versioned by pull
  date, not append-only. D-6.
- **Fresh from scratch.** Nothing in the master store is copied from
  `nse500_data*` or the backfill directories. Those stay as they are for
  production and become a cross-check only. D-7.
- **New membership files.** Production reads nothing from this program until
  a later, explicit decision. D-8.
- **Delisting at LTP.** A delisted position exits at its last traded price,
  no haircut. D-9.
- **One program.** This folder. D-10.

## Sources, verified 2026-09-10 (CONTEXT.md §6)

| Need | Source | Verified |
|---|---|---|
| Prices, live instruments | Kite historical API, day candles, adjusted | RELIANCE 2000-01-03 → today; ONGC adjustment ratio flat 0.977 pre-ex, 1.000 post |
| Prices, delisted | NSE bhavcopy raw × CA factors (D-11); GDF `GetHistory` as second opinion | bhavcopy serves every symbol from 1995; GDF floors 2009-01-01, ALBK served to 2020-03-19 |
| Symbol ↔ ISIN by day | NSE bhavcopy archive, direct download | legacy `cmDDMMMYYYYbhav.csv.zip` (ISIN column present by 2016, absent in 2005 — find the first year); UDiFF `BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip` from 2024 carries ISIN + company name |
| Corporate actions + company names | NSE `api/corporates-corporateActions`, cookie from the landing page | full calendar year per call; 2,208 rows for 2020 incl. dividend, split, bonus, demerger, buyback, AGM |
| Membership events | done — `tasks/index_reconstruction/` | exact today and Mar-2022 |

Not needed after all: Samco bhavcopy mirror, Playwright. Kept in reserve if
NSE starts throttling.

## Architecture

```
data/master/                       (gitignored except manifests + small tables)
  symbol_master.csv                isin, symbol, valid_from, valid_to, name, source
  membership/{nse500,nifty50,nifty100,nifty250}.csv     loader schema, PIT
  corporate_actions.csv            isin, symbol, ex_date, type, ratio/amount, source
  prices/kite/<SYMBOL>.csv         adjusted, as pulled, + pull_date in manifest
  prices/bhavcopy/<SYMBOL>.csv     raw, from the daily archive (every symbol, 2005 ->)
  prices/gdf/<SYMBOL>.csv          raw as served, cross-check only
  prices/adjusted/<SYMBOL>.csv     ONE basis: kite as-is; bhavcopy x CA factors for the rest
  manifest.json                    per file: source, first, last, rows, sha256, pulled_at, delisted_on
  qa/                              coverage by index x date, quarantine log, cross-feed report
```

A backtest reads `prices/adjusted/` + `membership/` through one loader.
Nothing reads the loose directories afterwards.

**Why a raw layer still exists under a total-return decision.** Kite is the
basis, but Kite cannot serve the 37 delisted names and cannot be audited
against itself. Bhavcopy closes are what actually traded; the CA table is
what NSE announced. Raw × factors must reproduce Kite's adjusted series to
the tick — where it does not, one of the three is wrong and the QA phase says
which. That reconciliation is also the only way the 37 GDF series land on the
same basis as the other 988.

**Versioning.** A dividend ex-date rewrites every prior row for that symbol.
The store keeps each pull under its date; a backtest records which snapshot
it read. Immutability is per snapshot, not per row — see D-6.

## Scope boundary

- Does not modify `nse500_data*`, `data/static/*`, `history_utils.py`,
  `apply_corporate_actions.py`, the daily pipeline, or anything the dashboard
  reads. The leak-sealing planned in `adjusted_price_series` is parked — it
  protected a price-return convention that no longer applies to research,
  and production is off-limits by D-8.
- Does not change strategy logic or parameters. Re-baselining is at current
  settings; the retune is `tasks/om25_retune_sf/` (not yet opened).
- Does not merge to `beta_gtm_mvp`.
- Options and cross-asset data out of scope.

## Critical files

- `tasks/index_reconstruction/` — membership events, resolvers, validators
- `data_pipeline/gdf_client.py`, `scripts/history_utils.py` (read-only here:
  `init_kite_client`, `fetch_history`, `resolve_instrument_token`)
- `data/instruments_full.csv` — Kite instrument dump (NSE + BSE, no ISIN)
- `tasks/adjusted_price_series/manifest_pre_flip.csv` — hash of the
  production panel as of 2026-09-08, the cross-check baseline
- `tasks/corporate_actions_fix/inventory.csv` — 99 suspected events to
  reconcile against the CA table
- `lib/audit_immutability.py` — the drift regression, reused on the store
