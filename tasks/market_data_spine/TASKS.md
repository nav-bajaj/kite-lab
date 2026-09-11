# Tasks

Ordered per PLAN.md. Owners: 👤 founder · 🤖 agent. Each phase ends at a gate;
the next does not start until the gate is met and recorded in RESULTS.md.

## Phase 0 — scaffold and probes ✅ 2026-09-10

- [x] Kite token live; day candles verified to 2000-01-03; adjustment method
      verified proportional (ONGC 0.977 → 1.000 at 2026-01-19)
- [x] NSE bhavcopy archive downloads directly, legacy and UDiFF formats
- [x] NSE corporate-actions API returns a full year per call
- [x] GDF authenticates, floors 2009-01-01, serves delisted history
- [x] Coverage: 1,025 all-ever symbols → 924 Kite NSE, 64 Kite BSE, 37 GDF
- [x] Founder decisions D-6..D-10 recorded; program consolidated
- [ ] Commit the two untracked folders this program depends on
      (`adjusted_price_series`, `panel_drift_audit_2026`) onto this branch

## Phase 1 — symbol master 🤖

- [ ] Bhavcopy fetcher: every trading day 2005 → today, legacy format to its
      cutover and UDiFF after; polite rate, resumable, cached under
      `data/master/raw/bhavcopy/` (gitignored)
- [ ] Find the first bhavcopy year carrying ISIN; before it, symbol only
- [ ] CA-API fetcher: every calendar year 2005 → today → `raw/nse_ca/`
- [ ] Build `symbol_master.csv`: ISIN-keyed, symbol validity windows from
      bhavcopy, company names from CA filings and UDiFF; encode the 62 known
      renames from `index_reconstruction/lib/renames.py` as checks, not inputs
- [ ] Resolve the 530 names in `index_reconstruction/data/unresolved_symbols.csv`
      through the master; record how each resolved, or why it did not
- [ ] **Gate (D-11):** for each of the four indices, at every event date,
      members resolved to a symbol with a bhavcopy row that day: ≥ 95% of
      index size from 2006-01-01, ≥ 98% from 2016-01-01. Residuals listed
      by name with the reason.

## Phase 2 — point-in-time membership files 🤖

- [ ] Emit `data/master/membership/{nse500,nifty50,nifty100,nifty250}.csv`
      in the `symbol,effective_from,effective_to,note` schema from the
      reconstruction + Phase 1 symbols. Production `data/static/*` untouched
- [ ] Re-run `index_reconstruction/lib/validate.py` and `validate_indices.py`
      against the new files: today exact, Mar-2022 factsheets exact
- [ ] **Gate:** validators pass; coverage table by index × year committed to
      RESULTS.md

## Phase 3 — fresh price pull 🤖

- [ ] Kite pull, adjusted, 2000-01-01 → today, NSE first then BSE fallback,
      for every symbol in the master Kite can resolve; 3 req/s, resumable;
      `prices/kite/`. Record pull date per file in `manifest.json`
- [ ] Bhavcopy series for every symbol Kite cannot serve, 2005 → last trade,
      from the archive already fetched; `prices/bhavcopy/`; `delisted_on` =
      last traded date (D-9: exit at LTP)
- [ ] GDF pull, raw, 2009 → last trade, for the same symbols, as a second
      opinion only; `prices/gdf/`
- [ ] Symbols neither feed serves: listed in `qa/no_feed.csv` with their
      membership spells, so the coverage gate can count them honestly
- [ ] **Gate:** every symbol in the master has a file or a `no_feed` row;
      coverage by index × date ≥ 95% from 2006, ≥ 98% from 2016, ≥ 99% from 2020

## Phase 4 — corporate-actions table 🤖

- [ ] Parse `raw/nse_ca/` into `corporate_actions.csv`: dividend (amount),
      split (old/new face value), bonus (ratio), rights (ratio, price),
      demerger, buyback; ISIN-keyed; drop AGM/interest rows into a side file
- [ ] Verify Kite's convention on ≥ 20 events across all types: compute
      expected factor from the CA row, compare to Kite's fresh÷bhavcopy ratio
      step. Record the formula Kite uses per event type, including whether it
      adjusts demergers (VEDL 2026-04-30 is the test case)
- [ ] Apply the same factors to the bhavcopy series of every non-Kite symbol
      → `prices/adjusted/`; Kite series copied through unchanged; GDF
      compared, never used as the basis
- [ ] Reconcile `corporate_actions_fix/inventory.csv` (99 flagged jumps): each
      is either matched to a CA row or logged as a bad print for Phase 5
- [ ] **Gate:** raw bhavcopy × cumulative factors reproduces Kite adjusted
      within tick rounding on a 50-symbol sample spanning 2005-2026; every
      mismatch explained

## Phase 5 — QA and cleanup 🤖

- [ ] Calendar: every date normalised to midnight; duplicate days collapsed;
      the panel calendar is the NSE trading calendar derived from bhavcopy,
      not the union of file dates
- [ ] Cross-feed: for each symbol, Kite÷bhavcopy ratio must be piecewise
      constant with steps only at CA ex-dates. Any other step is a bad print
      on one side; quarantine the row, never delete it
- [ ] Stale tails: a file whose last date precedes the calendar end without a
      `delisted_on` is an error, not a forward-fill
- [ ] Known cases handled explicitly: Tata Motors DVR second line,
      `DUMMY*` placeholders, the 16 no-feed symbols, INFY 2026-05-27,
      CASTROLIND July 2026
- [ ] **Gate:** `qa/report.md` shows zero unexplained steps, zero stale tails,
      zero phantom rows; quarantine log committed

## Phase 6 — master loader and re-baseline 🤖👤

- [ ] `data_pipeline/master_loader.py`: one function returns close/trade
      panels + membership fn from `data/master/`, with the snapshot date it
      read. Production loaders untouched
- [ ] Run OM25 v3, TL25 v3, L6 v2, COMBO at current parameters, 2006-01-01 →
      today, on the master. Compare against (a) today's published numbers and
      (b) the interim survivorship-free runs in CONTEXT.md §7
- [ ] Attribute every difference: universe / price basis (total vs price
      return) / corporate action / data fix. Unattributed = bug
- [ ] 👤 Review the re-baseline; decide the restatement framing
- [ ] **Gate:** RESULTS.md carries the four baselines with attribution; the
      OM25 retune task can open

## Phase 7 — standing procedure 🤖

- [ ] Daily: Kite append for live symbols; on any CA ex-date for a symbol,
      full re-pull of that symbol into a new dated snapshot (D-6)
- [ ] Weekly: CA-API poll → new rows into `corporate_actions.csv`; bhavcopy
      append; symbol-master diff (renames, new ISINs, delistings → D-9)
- [ ] Membership: poll the press-release archive, stage the diff, apply on
      the effective date — with the failure modes from CONTEXT.md §1 as tests
- [ ] `lib/audit_immutability.py --strict` adapted to the snapshot model and
      run against the store
- [ ] Runbook in `docs/market_data_spine.md`

## Parked (not lost)

- `adjusted_price_series` Phase 2-3 (seal the production panel's leaks): the
  research series no longer depends on it; production is off-limits by D-8.
  Reopen if production is ever moved onto this store
- The immutable published-decisions ledger (old Phase 3 here): unchanged in
  intent, deferred until the re-baseline settles what "published" means
