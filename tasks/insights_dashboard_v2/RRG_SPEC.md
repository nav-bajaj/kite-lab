# RRG — Relative Rotation Graph spec (sector rotation, universe-scoped)

The flagship addition. Two things make ours more than a clone of the
existing Indian RRG tools (StockMojo, SpikeDesk, TradingView scripts):
**universe-scoped sector composites** (sectors *within* Nifty 50 / 100 /
250 / 500 — no NSE index product offers this) and **RRG metrics as
first-class data** (quadrant, heading, velocity, distance feed tables,
lists and future scans — the Optuma move, not just a picture).

## 1. Methodology (JdK reconstruction — decision D3)

JdK RS-Ratio / RS-Momentum are proprietary; the community-consensus
reconstruction (matches StockCharts visually, preserves the key
universe-independence property) is the rolling z-score recipe:

```
RS(t)       = 100 · P_symbol(t) / P_benchmark(t)        # on adjusted closes
rs(t)       = ln(RS(t))                                  # log for ROC symmetry
RS-Ratio(t) = 100 + ( rs − SMA(rs, m) ) / StdDev(rs, m, ddof=1)
ROC(t)      = RS-Ratio(t) − RS-Ratio(t − k)              # on the normalized series
RS-Mom(t)   = 100 + ( ROC − SMA(ROC, m) ) / StdDev(ROC, m, ddof=1)
```

Proposed defaults (parameters, not constants — expose in the module
config, ship opinionated):

| Param | Weekly (default view) | Daily (tactical view) |
|---|---|---|
| bar | completed W-FRI resample | completed daily bar |
| m (normalization window) | 14 | 14 |
| k (momentum lookback) | 10 | 21 |
| tail (display) | 10 dots | 10 dots |

Non-negotiable properties (each is a spec test):

1. **Time-series normalization only** — each series z-scored against
   its own rolling history, never cross-sectionally. Adding/removing a
   sector must not move any other sector's dot or tail.
2. **Completed bars only** — weekly dots append at the weekly close;
   the in-progress week renders as a *provisional* dot (distinct
   style), replaced at the close. No look-ahead: signal at close of
   completed period.
3. **Warm-up**: first valid dot needs m + k bars; symbols short of
   history are suppressed with an explanatory note, never padded.
4. Quadrants at (100,100): Leading (>100,>100), Weakening (>100,<100),
   Lagging (<100,<100), Improving (<100,>100). Idealized rotation is
   clockwise; real tails skip and wobble — copy on the page says so.

Derived per-dot metrics (first-class API fields): `quadrant`,
`distance` (Euclidean from center), `heading` (compass angle of last
tail segment: 0°=N, 90°=E), `velocity` (length of last segment).

## 2. Universe scoping — the differentiator

### Mode 1 — Official sector indices (market convention)

Nifty sectoral indices vs **NIFTY 50** benchmark (convention across
Indian tools), weekly, 10-week tail. We already fetch 23 sectoral
indices daily with 2011+ history (`DATA_INVENTORY.md`). Ship the ~12
headline ones by default (BANK, IT, PHARMA, AUTO, FMCG, METAL, REALTY,
ENERGY, FIN SERVICE, PSU BANK, MEDIA, HEALTHCARE) with a picker for
the rest. Benchmark switcher: NIFTY 50 ↔ NIFTY 500 (tails recompute;
never mix benchmarks on one plot).

### Mode 2 — Universe-scoped super-sector composites (proprietary)

There is no NSE "Nifty 250" index and official sectoral indices are
not scoped to a universe. We build our own:

- For universe U ∈ {nifty50, nifty100, nifty250, nse500} and each of
  the 15 **super-sectors** (`data/static/zerodha_sectors.csv`), the
  composite is the **equal-weighted daily log-return mean of the
  sector's constituents within U**, chained into an index level.
- Membership is **effective-dated** (`data/static/*_membership.csv`,
  the universe_membership machinery) so historical tails don't carry
  survivorship bias — this matters because the drill-down *stocks*
  change over time even when the sector doesn't.
- Minimum constituent floor: a (universe, sector) cell with < 5 names
  is suppressed from the plot (shown greyed in the table with its
  count) rather than plotted on 2-3 stocks. Nifty 50 will only have
  ~8-10 plottable super-sectors; that is honest and fine.
- Benchmark for mode 2: the equal-weighted composite of **all of U**
  (apples-to-apples with the sector composites), with the official
  index available as an alternate. Note on page: roughly half the
  universe always sits left of 100 by construction — that is the
  point of a *relative* graph.
- Composites are computed once per day in the pipeline and persisted
  as a panel (`data/rrg/composites_<U>.csv`: date × sector level), so
  the API never rebuilds 17 years × 500 stocks on demand.

### Drill-down: sector → stocks

Clicking a sector opens the constituent RRG for that (universe,
sector) cell with an explicit benchmark toggle:

- **vs market benchmark** — positions comparable with the sector plot;
- **vs own sector composite** — pure intra-sector selection ("who is
  driving this sector").

The active benchmark is always labeled on the canvas. Stock tails use
`nse500_data_merged` (adjusted; corporate-action adjustment is
mandatory or RS lines jump — already handled by the pipeline).

## 3. Historical lookup & playback

- The engine computes the full RRG panel (all dots, all history), not
  just the latest tail. API takes `asof` and returns the tail ending
  there — the existing `?date=` snapshot picker therefore works for
  RRG for free.
- **Playback**: a date scrubber on a benchmark price strip under the
  plot (StockCharts pattern) + play button animating dot-by-dot, with
  keyboard arrow stepping. Implementation: client holds the windowed
  series (one payload with, say, 3y of dots per sector ≈ small — 12
  sectors × 156 weekly dots × 2 floats), so scrubbing is pure
  client-side rendering. Custom range picker: 1Y / 3Y / 5Y / Max.
- Daily ↔ weekly toggle; the two often disagree on quadrant — surface
  both, don't reconcile (JdK doctrine: weekly = strategic, daily =
  tactical).

## 4. UX spec (state-of-the-art checklist)

Canvas (custom SVG/canvas component — neither recharts nor
lightweight-charts does trailed scatters well; hand-rolled SVG with
d3-scale-style math in plain TS keeps deps flat, matches how
`SectorBars`/`RSSparkline` are already hand-built):

- Quadrant shading + corner labels; center crosshair at (100,100).
- Tails: per-dot markers, arrowhead on latest, thickness or opacity
  ramp toward the head; provisional current-period dot styled dashed.
- Hover: tooltip with sector name, RS-Ratio/RS-Mom, quadrant,
  week-of-date, mini price sparkline.
- Click-to-isolate (fade others), click-again to release; legend
  chips double as visibility toggles.
- Zoom/pan with fit + scale-lock buttons (auto-fit can breathe as
  tails move during playback — lock prevents seasick axes).
- **Synced table** (the analytical half): quadrant-colored rows,
  columns RS-Ratio, RS-Mom, quadrant, distance, heading (compass
  arrow glyph), velocity, tail % change; sorted by quadrant then
  distance; row hover highlights the tail and vice versa.
- Mobile: table-first with a static small-multiples quadrant chart
  (one mini-plot per quadrant), full canvas behind a "landscape"
  affordance.

Palette: quadrant fills/labels become theme tokens next to the
existing `--chart-series-*` so all six palettes stay coherent
(green/amber/red/blue conventions adapted per palette).

## 5. Compliance & copy

- Quadrant names are descriptive states; the Learn explainer must
  carry the empirical caution from Optuma's own white paper: quadrant
  *entry* is not a timing signal (Leading-entry forward returns were
  the worst of the four in their S&P study; rotation is
  clockwise-on-average, 62-92% transition consistency, with
  structural lag from normalization smoothing). We show rotation
  *state and history*; we do not say "buy Improving".
- No forward-return claims on our own data unless a validity study
  passes the protocol (a sector-rotation validity study would be a
  separate research probe; not required for launch since we make no
  claims).
- Tooltip/table labels reuse the closed lexicon; new terms (heading,
  velocity, quadrant names) go into the glossary.

## 6. Engine & API shape

- `kite-api/app/insights/rrg.py` (TDD per policy):
  - `compute_rrg_panel(symbols, benchmark, timeframe, m, k)` →
    MultiIndex (symbol, date) frame of ratio/momentum/derived fields;
    mtime-invalidated cache like siblings.
  - `get_rrg_snapshot(mode, universe, benchmark, timeframe, asof, tail)`.
  - Composite builder `build_universe_composites(U)` in the daily
    pipeline (after `sync_insights_panels.py`), writing
    `data/rrg/composites_<U>.csv`.
- `GET /api/insights/rrg?mode=&universe=&benchmark=&timeframe=&asof=&tail=&range=`
  → `{params_echo, benchmark_series (for the scrubber strip), sectors:
  [{key, label, n_constituents, dots: [{date, ratio, momentum,
  quadrant, distance, heading, velocity, provisional}]}]}`.
  Unauthenticated read like siblings; 15-min cache; payload budget
  <150 KB (3y weekly × 15 sectors is comfortably inside).
- `GET /api/insights/rrg/constituents?universe=&sector=&benchmark_mode=`
  for the drill-down.

Spec tests (write first): synthetic outperformer/underperformer with
known rotation direction; universe-independence (drop one symbol,
others' dots byte-identical); warm-up NaN policy; W-FRI completed-bar
resample (a Wednesday `asof` must not create a partial weekly dot,
must mark provisional instead); ddof pinned; quadrant/heading/
velocity math on hand-computed fixtures.

## 7. Sources

Methodology reconstructions and UX patterns per the research sweep:
StockCharts ChartSchool RRG + RRG tool docs; Optuma/Verdouw white
paper ("Buying out-performers is too late", 2016) + RRG scripting
docs; OpenBB `relative_rotation.py` (12-1 log momentum variant);
RRGPy, RRG-Lite wiki, RRG-Sector-Rotation-India comparison doc;
Bloomberg RRG partner docs; Indian conventions from StockMojo /
SpikeDesk / TradingView "RRG India" (sectorals vs Nifty 50, weekly,
10-week tail).
