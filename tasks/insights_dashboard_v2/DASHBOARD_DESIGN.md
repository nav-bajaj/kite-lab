# Dashboard design — information architecture and module specs

Principle: every module = **today's value + historical context + how to
read it**. Cards without charts are demoted; charts without a "so what"
framing are not shipped. The user should always be one glance from
"where are we now" and one click from "how did we get here".

## 1. Information architecture

Current (3 linked tabs + 2 orphans):

```
Pulse | Screener | Learn        (+ unlinked: /sectors, /watchlists)
```

Proposed (4 tabs, guided-first):

```
Pulse | Sectors & Rotation | Stock Lists | Learn
                                └─ Explore (screener, demoted entry point)
```

- **Pulse** — the market dashboard. Regime, stress, breadth, VIX,
  concentration, movers; each headline metric charted historically.
- **Sectors & Rotation** — the RRG flagship (see `RRG_SPEC.md`) +
  sector breadth/RS detail. Absorbs today's orphaned `/sectors`.
- **Stock Lists** — the four curated lists as first-class named
  products (below), absorbing and replacing `/watchlists` and the
  screener presets.
- **Learn** — unchanged surface, extended with new explainers (RRG,
  each curated list, each charted indicator).
- **Explore (screener)** — no longer a tab. Reached from "Explore all
  500 stocks" links at the bottom of each list and from stock pages.
  Same component, demoted placement. The built-but-unshipped filter
  rail (`_client.tsx` implements `matchFilters` with no UI) gets a
  minimal UI here, since presets move out to Stock Lists.

Navigation/shell: `/insights` moves from marketing chrome to the
primary product shell (decision for the founder: promote the insights
layout to be the signed-in home, with portfolios demoted behind the
admin flag — the frontend exploration confirmed nav is centralized in
`src/lib/nav.ts` + `bottom-nav.tsx` SLOTS + `navbar.tsx` pathNames, so
this is a small, contained change).

## 2. Pulse as a dashboard

Layout: headline strip → chart modules → movers rail. All modules read
the same `?date=` snapshot param (the time-machine picker stays — it is
a differentiator and it already works).

### 2.1 Headline strip (top row, always visible)

Regime badge · Stress gauge · Breadth headline (% above 200-DMA) ·
INDIA VIX · Nifty 50 day change. Each is a compact stat tile; clicking
scrolls to (or expands) its chart module. During market hours, tiles
carry a "live · updated HH:MM" pill (see REALTIME_SPEC).

### 2.2 Chart modules (the core change)

Each module: current value + reference bands + a `lightweight-charts`
time series with range picker (6M / 1Y / 3Y / 5Y / Max) and an
optional Nifty overlay for context. Backed by existing panels — most
of this is API plumbing, not new math.

| Module | Series | Reference bands (from breadth_atlas) | Backend status |
|---|---|---|---|
| Market breadth | `pct_above_200dma` (+ selectable 50/100/21-DMA, % advancing) | p5 = 22% "washed out", p95 = 94% "saturated", median 59% | `/breadth/timeseries` EXISTS |
| Stress composite | 0-100 score + components | quintile shading | `/stress/timeseries` EXISTS |
| Regime ribbon | 4-state regime as colored band under the Nifty chart | — | `/regime/history` EXISTS (episodes) |
| INDIA VIX | close + z-score bands | z ±2 | needs `/macro/timeseries` (panel exists) |
| Net new highs | `net_new_highs_pct` | asymmetry note (crashes cluster lows) | in breadth panel, EXISTS |
| McClellan oscillator | `mcclellan_osc` | ±1σ / ±2σ | in breadth panel, EXISTS |
| Concentration | top-5 share of Nifty move, cap-vs-equal-weight spread | — | needs timeseries endpoint (panel exists) |

Curation rule from the atlas PCA: the panel is really 2 factors (slow
participation + fast flow). Ship **one headline chart per factor**
(breadth 200-DMA for level, McClellan/AD for flow) and put the rest
behind a metric selector inside the module — do not tile 14 charts.

### 2.3 Movers rail

Fresh 52w highs/lows and RS improvers stay, but each name chips into
its stock page, and each rail links into the relevant curated list
("see all volume surges →").

## 3. Stock Lists — the four curated products

Each list gets: a name, a one-line thesis, the transparent criteria on
the card, the current constituents (sortable, with the relevant columns
for *that* list), a small historical panel ("names entering/leaving,
count over time"), and a Learn explainer. Detectors follow TDD policy
(synthetic fires/doesn't-fire panels); any forward-return copy passes
the validity protocol first.

| List | Basis (existing engine support) | Gap to close |
|---|---|---|
| **Volume surges** | `vol_ratio`, `vol_ratio_5d`, `updown_vol_ratio_20d`, Volume Confirmation score, `Volume expansion` tag | Formalize detector (e.g. vol_ratio ≥ 2 + price context + liquidity tier floor); intraday variant needs time-of-day volume curve (REALTIME_SPEC) |
| **Coiled fresh momentum** | `coiled_springs` watchlist (tight range near 50-DMA, low vol, above 200-DMA) + `New momentum` tag + `rank_delta_21d` inflection cohort | Merge "coiled" and "fresh momentum inflection" into one detector; inflection validity verdict was observation-only — copy stays descriptive |
| **Custom relative strength** | `rs_rank.py` composite (10/20/30/40 weights over 1/3/6/12m percentiles), sector-relative rank; rs_top_decile PASSED validity (+1.19pp 20d excess) — badge allowed | Mostly presentation: top-decile list + rank-history sparkline per name (needs cheap rank-history, see below) |
| **Trend & consistency** | Trend Score + Momentum Consistency score, `sustained_uptrend` watchlist, `pct_positive_weeks_6m` | Combine into one ranked list; define the published cutoff |
| (secondary) Breakouts / Breakdowns | existing watchlists | Keep reachable inside Stock Lists as "more lists", not top-level |

Backend gap that matters for all four: **per-stock indicator history is
point-in-time** (stock_metrics/rs_rank/scores build one cross-section
per date; rank history is recomputed at 21-day sampling). To draw list
membership over time and per-name rank sparklines cheaply, persist a
small daily cross-section (date, symbol, rank, scores, tags, list
membership) — append one ~500-row slice per day from the 16:30
pipeline, exactly like `sync_insights_panels.py` does for prices. This
also un-blocks "score history" that insights_v2 dropped for cost
reasons. CSV/parquet panel first; DB table only if query patterns
demand it.

## 4. Sectors & Rotation

- **RRG front and center** — spec in `RRG_SPEC.md` (universe scoping
  Nifty 50/100/250/500, trails, playback).
- Sector strip under it: per-sector cards (RS rank, % above 200-DMA,
  breadth thrust flags) from `sector_rs` + `sector_breadth` —
  clicking a sector opens the detail (existing `/sectors/{name}` 252d
  history endpoint) plus its constituent list scoped to the selected
  universe.
- Subgroup spreads (PSU vs private banks etc.) stay as a
  differentiated deep-dive block.

## 5. Visual & component notes

- Standardize on **lightweight-charts** for time series (already
  themed via the CSS-var probe pattern in `stocks/[symbol]/_chart.tsx`;
  reuse that). The RRG is a custom scatter/trail canvas — recharts or
  hand-rolled SVG/canvas; decide in RRG_SPEC.
- The six-palette system already defines `--chart-series-1..3` per
  palette; extend tokens for RRG quadrant fills and regime-band colors
  so all palettes stay coherent.
- Existing patterns to reuse: `(dashboard)/dashboard/page.tsx`
  stack-of-sections composition; `metrics-grid` KPI tiles;
  `flash-on-change` for live tick updates; `freshness-panel` status
  dots for the "as of" indicator.
- Mock the IA in Pencil and get founder sign-off on direction before
  component work (per standing feedback: visual-validate first).
- Mobile: chart modules collapse to sparkline + value; lists keep the
  existing mobile card fallback pattern from the screener.

## 6. Copy & compliance

- Every chart module carries a one-line "How to read" + Learn link.
- Reference bands are labeled descriptively ("historically rare
  territory: bottom 5% of days since 2010"), never prescriptively.
- Extend the lexicon tests to all new module titles, band labels, list
  names and empty states.
- Screener demotion removes the presets (they become Stock Lists);
  remaining explore surface keeps the standard disclaimer footer.
