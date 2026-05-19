# Plan: Marketworks Rebrand + Portfolio Naming

## Context

Company name decided: **Marketworks**. The dashboard, deployed at
`kite-lab.vercel.app`, should reflect that going forward. We also haven't
named our portfolios for the user — they currently surface internal
research identifiers (NSE 500 / Nifty 100 / Nifty 250), and 4 production
portfolios that the backend builds daily aren't surfaced in the UI at
all.

This branch does both: a cosmetic Kite-Lab → Marketworks rebrand on
visible dashboard surfaces, plus the addition of all 7 portfolios to the
universe selector with descriptive names.

**Scope is deliberately bounded:**
- No URL change (`kite-lab.vercel.app` stays). Renaming Vercel domains
  is a separate infra task.
- No repo / directory rename. Every absolute path, daily-pipeline
  script, Mac mini handover doc, and venv stays valid.
- No DB schema change. Internal `universe_id` values stay identical;
  only display names change.
- No backend code change for the new portfolios — backend
  (`kite-api/app/config.py:150`) already supports all 7 universe IDs.

## Approved portfolio names

Universe selector renders these (no "Marketworks" prefix — that lives on
brand surfaces only):

| Internal ID | Old display | New display |
|---|---|---|
| `om25_v3` | OM25 v3 | **Quality Momentum** |
| `tl25_v3` | TL25 v3 | **Trend Leaders** |
| `l6_v2` | L6 v2 | **Core Momentum** |
| `combo_defensive` | COMBO Defensive | **Defensive Blend** |
| `nse500` | NSE 500 | **Broad Momentum** |
| `nifty100` | Nifty 100 | **Large-Cap Momentum** |
| `nifty250` | Nifty 250 | **Mid-Cap Momentum** |

Brand surfaces show **Marketworks** (login page title, sidebar logo
text, mobile sidebar, browser tab title, README header).

## File changes

### Universe definitions (frontend)

- `kite-dashboard/src/lib/types.ts:2` — extend `UniverseId` to include
  the 4 new IDs.
- `kite-dashboard/src/lib/universes.ts` — rewrite `UNIVERSES` to hold
  all 7 entries with their new `name`, `shortName`, `description`,
  `stocks`, `riskProfile`. Add a sensible `DEFAULT_UNIVERSE` ordering:
  most-used first (Quality Momentum / Trend Leaders / Core Momentum /
  Defensive Blend / Broad Momentum / Mid-Cap / Large-Cap).
- `kite-dashboard/src/components/shared/universe-selector.tsx` — likely
  unchanged if it reads from `UNIVERSES` reactively; verify.

### Brand surfaces

- `kite-dashboard/src/app/layout.tsx:17` — `title: "Marketworks Dashboard"`.
- `kite-dashboard/src/app/login/page.tsx:26,81` — "Marketworks Dashboard".
- `kite-dashboard/src/components/shared/sidebar.tsx:43-45,104` — logo
  initial "M", brand text "Marketworks", footer "Marketworks v1.0".
- `kite-dashboard/src/components/shared/mobile-sidebar.tsx:33-37,66` —
  same as above.
- `kite-dashboard/src/contexts/universe-context.tsx:14` — bump
  localStorage key from `kite-lab-universe` to `marketworks-universe`
  (graceful: read old key first, migrate, write to new).
- `kite-dashboard/next.config.ts` — verify if any "kite-lab" reference
  exists; if so, update.
- `kite-dashboard/package.json:2` — `"name": "marketworks-dashboard"`.
- `README.md` — top-level rebrand.

### What I will NOT touch

- DB schema, migration files, `equity_curve` / `metrics` / `trades` /
  `holdings` tables.
- Backend universe IDs in `kite-api/app/config.py` — already correct.
- Daily pipeline scripts, CSV directory names, portfolio_dir paths.
- `CLAUDE.md` — keep internal research IDs (OM25 v3 etc.) since they're
  load-bearing for code/runbooks. Add a note pointing to display names.
- The URL `kite-lab.vercel.app` — leaving the Vercel domain alone.

## Verification

1. `npm run build` clean.
2. `npm run lint` clean (eslint-security from R-007 doesn't false-positive).
3. Manual dashboard pass after `npm run dev`:
   - Login page reads "Marketworks Dashboard".
   - Sidebar shows "M" logo + "Marketworks" text + "Marketworks v1.0".
   - Universe selector lists all 7 portfolios with new names.
   - Each page (Dashboard, Open Positions, Performance, Rebalance,
     Trades, Admin) renders under each of the 7 universe selections.
4. Page-by-page status table written into this folder
   (`tasks/name_change/VERIFICATION.md`) for any page that doesn't
   support a new universe — recorded as follow-up, not a blocker.

## Known gap — addressed in follow-up commit

**Resolved:** `kite-api/app/services/rebalance_service.py` was extended
with 4 new `elif` branches mapping each new universe to its
`data/<strategy>_portfolios/<strategy>_portfolio_202*` directory. All 7
universes now resolve cleanly via `get_latest_signals_dir` (verified by
direct call — see commit message).

**Caveat preserved:** the new v3 portfolio runners
(`run_om25_v3_portfolio.py`, `run_tl25_v3_portfolio.py`, etc.) emit
`<strategy>_signals.csv` / `<strategy>_exits.csv` / `<strategy>_trades.csv`
— **not** the legacy `changes_<date>.csv` / `orders_<date>.csv` format the
rebalance UI consumes. Result: on /rebalance for any of the 4 new
portfolios, the dashboard will show the "No changes file found" /
"No orders file found" message rather than crashing. Full rebalance-UI
support for the v3 strategies requires either:

- Adding `changes_*.csv` + `orders_*.csv` output to the v3 runner
  scripts, OR
- Adapting `rebalance_service.get_rebalance_preview` /
  `get_rebalance_orders` to read the v3 `<strategy>_signals.csv` format
  directly.

Either path is a separate task — graceful degradation is in place.

## React 19 lint errors — addressed in follow-up commit

**Resolved:** `kite-dashboard/src/components/positions/positions-table.tsx`
was refactored to move the inline `SortableHeader` arrow-function
component out of `PositionsTable`'s render body and up to module scope.
`handleSort` is now passed as the `onSort` prop. Closes the 10
`react-hooks/static-components` lint errors surfaced by the Next 16 +
React 19 strict-mode rules.

## Out of scope (future work)

- Rename Vercel project / point custom domain to marketworks.
- Rename Railway service.
- Rename GitHub repo / local directory.
- Wire `rebalance_service` to the 4 new portfolios.
- Update sync_to_production paths if any reference "kite-lab" literally.
- Add Marketworks favicon + better logo (currently just "K" / "M" initial).
