# Decisions log — insights_dashboard_v2

## 2026-08-13 — founder reconciliation round

**D1 (intraday posture): DECIDED — go live.** Founder approved the live
data route. Engineering target is posture C from `REALTIME_SPEC.md`
(live *derived* indicators; no public per-stock live quote display
until a data agreement exists). Still required before public exposure:
risk-register row documenting the posture + labels ("provisional",
timestamp) as built. Multiple Kite Connect apps are available if
needed (see streaming note below) — note that extra API keys add
capacity/redundancy, not licensing cover.

**Cross-asset module: OUT of scope.** Dropped from the new dashboard.
It was barely wired anyway (only india_10y live; USDINR/gold/crude
registered `data_available=False`). INDIA VIX stays — it is part of
the macro/stress stack, not cross-asset. The global/commodity/rates
rows in `tracked_indices.csv` keep fetching (cheap, harmless) but
nothing in the new UI surfaces them.

**App placement: inside kite-dashboard, promoted to primary.** Insights
does not become a separate app. It stays in the same Next.js app and
becomes the signed-in home surface; portfolio pages demote behind the
admin flag (reversible when regulatory approval lands). Rationale:
shared Supabase auth, palette/token system, API client, CSP, and one
Vercel project on marketworks.in. A separate app would duplicate all
of that and force a microfrontends setup for one domain — available
later if ever needed, unnecessary now.

**Streaming design: single Kite websocket connection.** KiteTicker
supports up to 3,000 instrument tokens per connection (3 connections
per API key). Our full live set — NSE 500 stocks (~534 tokens) + 40
tracked indices — fits in ONE connection with 5x headroom. So:
no multiple API keys needed for data volume; a second app key is
useful only as failover or to separate the trading login from the
data login. Implementation ladder (see REALTIME_SPEC §2):
1. Start with REST polling (`quotes_service.py` already wraps batched
   `kite.quote()`; 500 instruments = one call) driven by the existing
   APScheduler — good to ~1-min cadence, fewest moving parts.
2. Upgrade to a KiteTicker consumer (quote mode — we need volume for
   surge counts) writing an in-memory tick state that the snapshot job
   reads, when/if we want sub-minute freshness.

**Historical data: no new granularity needed.** Daily (17y, merged) +
hourly (`nse500_data_hourly/`, already fetched daily) covers
everything planned: RRG needs daily/weekly; breadth history is daily;
the time-of-day volume curve calibrates fine from hourly bars. Minute
data is NOT needed for launch and can be fetched retroactively from
Kite if a future feature demands it. Index intraday history: not
needed — the live layer produces today's intraday curve going
forward; no backfill required.

**Nifty 250 composition: CONFIRMED.** `nifty250_universe.csv` =
all 100 Nifty 100 names + 150 midcap names (verified disjoint from
the smallcap 250 universe) — structurally NSE's NIFTY LARGEMIDCAP 250
(defined as Nifty 100 + Nifty Midcap 150). The official
`NIFTY LARGEMID250` index is already in the daily fetch and serves as
the official-index benchmark analog for our nifty250 universe in RRG
mode 2.

## 2026-08-14 — mock + follow-up questions

**Quality Momentum universe: VERIFIED custom, recommend keeping it.**
OM25 v3 reads `data/static/nifty250_universe.csv` (`scripts/om25_v3.py:42`)
with effective-dated masking via the membership machinery — NOT the
official NIFTY LARGEMIDCAP 250 constituent list. Since our list is
built by the same recipe (Nifty 100 + Midcap 150, verified 2026-08-13),
the two should track closely but can drift between our refreshes and
NSE's rebalance dates. Recommendation (founder to confirm): keep the
custom universe as the portfolio + RRG source (stable `nifty250` ID in
DB/CSVs, membership history, backtest continuity); add an official
LARGEMID250 constituent download as a reconciliation CHECK at each
NSE reconstitution (diff report, not an automatic switch).

**Personalization (watchlists/alerts): architecture documented** in
`PERSONALIZATION.md`. Headline: two API planes — the public cached
insights surface never carries per-user data; a new authenticated
`/api/me/*` namespace (Supabase JWT) holds watchlists/alerts/
notifications in three Postgres tables; alerts evaluate in the
existing scheduler against engine snapshots; entitlements_v1 limits
map onto watchlist/alert capacity. Schema-ready now, build post-launch.

**Mock**: `mock_insights_dashboard.pen` (3 screens: Pulse, Sectors &
Rotation/RRG, Stock Lists) + PNG exports in `mock_previews/`. Built on
the vendored Mint tokens (mist bg, lichen primary, Fraunces display,
Outfit UI, accent-rotation chips, chart-series colors) so it matches
the existing dashboard language. NOTE: the .pen must be saved from the
VSCode Pencil tab to persist (MCP edits live in the editor session).

## 2026-08-14 — IA revision: sidebar + mission control

Founder direction: the top nav bar belongs to the website
(Portfolios / Library / Insights) — insights tabs must NOT live there.
New IA (full spec in `DASHBOARD_DESIGN.md` §1):

- Insights gets its own **sidebar** (same shell pattern as the
  portfolio dashboard: icon + label, active pill).
- The home surface is a **mission-control Overview**: compact
  indicator cards grouped into MARKET / SECTORS & ROTATION /
  STOCK LISTS sections, each card = value + sparkline + one-liner +
  expand affordance.
- Expanding a card opens the indicator's **detail view**: back button
  to Overview + a sub-rail listing the section's sibling indicators
  + full chart, stats strip, and a "what this measures" learn panel.
- Screener stays in the sidebar as the last analytics item (the
  explore escape hatch); My Watchlist has a reserved slot ("soon").

Production reference screenshots captured via Playwright (admin
session) in `prod_reference/` — the mock's shell, spacing, and Ocean
palette follow `prod_dashboard.png`. Mock rebuilt accordingly
(4 screens, exports in `mock_previews/v2_*.png`). The v1 top-tab
Pulse screen is kept in the .pen as "OLD v1 (superseded)".

## 2026-08-14 — indicator review rounds (post-Slice-2.5)

Founder reviewed the built dashboard live. Decisions, as implemented:

- **Universe selector** in the top bar (next to snapshot): Nifty 500
  default, plus 250 / 100 / 50. Our custom nifty250 construction used
  (Nifty 100 + Midcap 150); for concentration's cap side its official
  analog NIFTY LARGEMID250 is the index series. Scopes the breadth
  family AND concentration; market-wide gauges (VIX, stress) ignore it
  by design. Atlas reference bands only label the Nifty 500 scope —
  other universes compute bands from their own history.
- **Market section navigation = one horizontal browser-style tab row**
  (active tab is a raised card), identical on every page of the
  section — never a different menu at different depths. Order: Regime
  first (the word is "Regime"), then Stress, Breadth, Advances &
  declines, Net new highs, McClellan, India VIX, Concentration.
- **"Daily read" page removed** — it duplicated the Overview.
  /insights/market redirects to the Regime tab.
- **Regime detail arc**: first read as "remove the detail" —
  corrected: the detail STAYS (timeline, spells, four-states legend);
  only the conditional-distribution forward-return table ("what
  followed days like these") is banned from it as suggestive.
- **New indicator: Advances & declines** (raw daily net advances +
  cumulative A-D line) as card + detail.
- **Movers + RS climbers belong to Stock Lists**, not Market — strip
  moved under the lists section on Overview; full block on
  /insights/watchlists (page retitled "Stock Lists").
- **Concentration expanded to all four index scopes** (was Nifty 50
  only); per-name attribution stays nifty50-only (factsheet weights)
  with an explicit note elsewhere.
- **Next**: founder wants an indicator-by-indicator deep dive; "a lot
  of nitty gritties to be tackled."

## 2026-08-15 — deep dive, tab 1: Regime

Founder notes on the Regime tab, as implemented:

- **The chart is the index, not a timeline.** Show the universe's own
  index with the regime as a light colour overlay on it — reading the
  regime against the price it produced is the point. Each universe
  plots from the date its own index series begins. Standard range
  picker (6M/1Y/3Y/5Y/Max, defaulting to Max).
- **Regime is defined per universe.** A Nifty 500 Trend Bull reads the
  NIFTY 500's trend and the NSE 500's breadth — not the Nifty 100's.
  `compute_regime_panel(universe)` scopes both inputs; India VIX stays
  shared because there is no per-universe volatility index.
- **History depth is bounded by the index series**, and differs per
  scope: Nifty 100 / Nifty 50 from 2010, Nifty 500 from May 2015,
  Nifty 250 (LARGEMID250) from May 2020. Founder accepted this
  explicitly ("from the point that we have the data for that one").
- **The legacy market-wide panel is retained** for the note generator,
  conditional distributions and calendar lookbacks — `compute_regime_
  panel()` with no argument is unchanged (NIFTY 100 trend + NSE 500
  breadth, 2010+). Those surfaces would otherwise silently lose five
  years of base-rate history. **Open (D5): should the Daily Quant Note
  adopt the universe-scoped regime, accepting the shorter history?**
- **Stat tiles**: median spell length for each of the four regimes,
  plus the index's move since the current spell began. The total count
  of spells on record is dropped — it wasn't telling anyone anything.
- **Recent spells list** carries what the index did across each spell
  (close to close, coloured by sign).
- **Language standardised to "Regime"** — the word "state" is gone
  from the UI.
- **Explainers are stated plainly.** The four-regime cards no longer
  hide their rule behind a "See the exact rule" disclosure; the rule
  is printed under the plain-English meaning, and it names the
  selected universe's index and breadth. The bottom panel is retitled
  "Learn more" (applied to every Market tab for consistency).
- **Removed while in there**: the Stress card in the four-regime
  legend carried a forward-return claim ("median +3% over the next 20
  days... the 'buy panic' zone, statistically"). That contradicted the
  2026-08-14 decision banning forward-return content from the regime
  detail, and it was live. It is gone. **Note the `/insights/learn/
  regime` explainer still contains the same class of claim** and is
  one click away via "Read the full explainer" — flagged for the D4
  compliance pass, not edited unilaterally.

## 2026-08-15 — Regime, round 2 (rules redefined)

- **Regime rules now run on 50-day windows.** Founder redefined them:
  the index against its **50-day** average (was 100) and participation
  as the share of the universe above their own **50-day** averages
  (was 200). Thresholds unchanged (55% / 85% + VIX z < -1 / VIX z >
  1.5 or below-trend with < 35%). Applies to the universe-scoped
  panels only; the legacy market-wide panel keeps 100/200 (D5 still
  open). The windows now travel on the snapshot
  (`trend_ma_days`, `participation_ma_days`) so the displayed rule text
  is generated from the engine and cannot drift from it again.
- **Consequence — the regime is much twitchier.** On Nifty 500 the
  median Drift spell fell from 16 to 8 days and episode count rose to
  147. At the new 1-year default the tint reads as narrow stripes.
- **Consequence — STRETCHED is nearly extinct on the broad universes**:
  3 spells in 11 years on Nifty 500, 3 on Nifty 250, versus 8 (Nifty
  100) and 10 (Nifty 50) since 2010. >85% of 500 names above their
  50-DMA *and* VIX a full sigma below its year is a very rare joint
  condition. Flagged for the founder — a regime that fires three times
  a decade may want a looser threshold or a merge into Trend Bull.
- **Chart default is 1 year** (was Max).
- **VIX wording fixed**: "above its own year" read as a half sentence;
  now "more than 1.5 standard deviations above its average of the past
  year".
- **Copy**: chart sub is "The index with an overlay tint by regime in
  force. One of four rules-based regimes, smoothed with a 3-day
  confirmation."; legend intro trimmed to one sentence; the
  close-to-close footnote under Recent spells and the 3-day-smoothing
  footnote under the legend are removed.
- **Fourth stat tile added** — Participation (the classifier's own
  breadth input) so the row of tiles fills evenly instead of leaving a
  gap at the right.

## 2026-08-15 — copy-review loop: Vercel Toolbar on localhost

Founder wants to mark up copy on the page instead of dictating notes
into chat, and wants it **local** — no preview deployments in the loop.

**Built**: `@vercel/toolbar` as a dev dependency, `withVercelToolbar()`
wrapping `next.config.ts`, `<VercelToolbar />` mounted in the root
layout behind `NODE_ENV === "development"`. CSP gains `vercel.live` +
Pusher websockets **in development only** — both constants collapse to
`""` in production, verified against a real `next start` build, so the
deployed CSP is unchanged and no register row is owed (R-006/R-007).
The toolbar loads and its launcher renders on localhost.

**Blocked, honestly**: the plan was for the agent to read comment
threads back through the Vercel MCP connector. It cannot —
`list_teams` returns `[]` for this account and `list_toolbar_threads`
errors, consistent with the known 403 on this team (see the
`reference_deploy_verification` note). So the founder can comment, but
the agent cannot yet read the comments programmatically.

**Resolved (same day)**: founder ran `vercel login`, and the read path
now works through the CLI token rather than the MCP connector. The
endpoint is `GET /v1/toolbar/threads?teamId=&projectId=&status=` —
undocumented in the public REST reference, found by probing, so treat
it as liable to change. Wrapped in
`tasks/insights_dashboard_v2/read_comments.py`; run it after a review
pass to print every unresolved thread with its page and anchor.

**The loop works, round 1 done.** Founder left 10 comments on the
Regime tab; all 10 were read, applied, replied to and resolved from the
terminal without anything being retyped. Three scripts/endpoints:

| Step | How |
|---|---|
| Read notes | `read_comments.py` → `GET /v1/toolbar/threads` |
| Reply + resolve | `reply_comments.py` → `POST .../{id}/messages`, `PATCH .../{id}` |

The payload's `context.selection` carries the **exact on-page text** a
note is pinned to, which is what makes the notes actionable; when the
founder pins without selecting text, `context.frameworkContext` gives
the React element path instead and the target has to be inferred.
Selecting the text first makes it unambiguous — worth doing where the
note is about specific wording.

One blocker fixed on the way: `Cross-Origin-Opener-Policy: same-origin`
nulls `window.opener` for cross-origin popups, so the toolbar's
"Continue with Vercel" window loaded blank and could never hand the
session back. Development now sends `same-origin-allow-popups`;
production still sends `same-origin` (verified against a real build).

Also fixed while here: `REVALIDATE_SECONDS` is now 0 in development.
The 15-minute fetch cache was serving `/reading` responses captured
before a backend field existed, which is what made the Participation
tile look empty on non-default universes.

## 2026-08-15 — Regime, comment rounds 3-4

Round 3 (10 notes): "Now" card → "Current regime"; previous-regime card
reads "day N" like its neighbour; "since the regime began" and the
"regimes vary widely" line dropped; legend heading "The four regimes
explained:"; all four regime descriptions replaced with the founder's
wording; "Latest" button lifted out of the snapshot popover into the
bar.

Round 4 (5 notes): the four cards moved **above** the chart (state
first, chart as backup); the "Latest" button became "Today" with an
icon, live only when on another date; the Market Pulse tab row no
longer shows scrollbar chrome (`.mw-no-scrollbar` in globals.css);
**candlestick view** added alongside the close line; **crosshair
readout** showing date + OHLC + that day's regime beside the index
name. `/regime/timeseries` now returns open/high/low/close, not just
close (`regime_index_ohlc`).

**Two snapshot bugs found by reviewing on a rewound date**, both from
pairing a rewound reading with un-rewound history:
1. The "this regime" card read the *newest* episode, so the COVID
   snapshot showed Stress next to +2.4% (August 2026's move). It now
   finds the episode the reading sits in, and Recent regimes stops at
   the reading date.
2. That figure covered the whole episode, including days after the
   snapshot. It is now computed from the close series up to the
   reading date — 23 Mar 2020 reads -32.0% (the move so far) rather
   than -18.1% (including an April recovery that had not happened).

**Closed (round 5)**: the chart now stops at the snapshot date too, so
the Regime tab rewinds *in full* — the time machine is strict here.
The footer disclaimer is conditional: on Regime it says readings and
chart both stop on that day; the other seven tabs keep the old wording
because their charts still run to the latest close. **The same fix is
owed on those seven** — take it as each tab comes up for review.

Still open: candles are very dense at 3Y+ (2,700 bars); consider
capping the candle view to shorter ranges or falling back to the line.

**TAB STATUS: Regime is DONE** (founder, 2026-08-15) — 15 comments
across two rounds, all applied and resolved.

## 2026-08-15 — Stress + Breadth (deep dive tabs 2-3)

**Index overlay, now a shared capability.** Founder: most of these
gauges only mean something against price. `GET
/api/insights/index/timeseries?universe=` returns the scope index's
close; `TimeseriesChart` takes an optional `overlay` and draws it
**rebased to percent change from the left edge of the visible window**,
on its own hidden scale, behind a toggle. Rebasing (not raw level) was
the founder's own suggestion and is what makes the two readable
together. Live on Stress and Breadth; reusable for the remaining tabs.

**A real bug in the stress drivers card.** The engine scores each
component 0-100; the card multiplied by 100 again, so every bar
overflowed to full width and the numbers read ~2659 instead of 27.
Founder spotted it as "the numbers seem off, and all the bars look
alike". Fixed, and each row now shows its weight.

**Displayed rules are now read from the engine, not retyped.** Stress
ships `weights`, `percentile_window_days` and `component_window_days`
on its snapshot; the "How the score is computed" bullets and the
percentile caption render from those. (I had drafted the bullets from
memory and got the weights wrong — 30/30/25/15 instead of the real
35/25/20/20. Same class of error as the regime copy claiming 100/200
windows. Hence the rule: if the UI states a number the engine owns,
the engine ships it.)

**Answers to the founder's three questions**, all from source:
- Score percentile is over **5 years** (252*5) — not all history, not
  one year. Caption now says so; easy to retune, it is one constant.
- VIX percentile is **1-year rolling** (252d) — his guess was right,
  and it is now shown on the card (p27 today).
- "Recent high" meant the **highest close of the trailing 252 days**.
  Copy now says "below its 1-year high".

**Copy**: "Market Stress Composite" / "Market Breadth {universe}";
"Now" → "Current score"; per-metric one-line explainers on every
breadth chip; the dashed-line caption removed. Founder's stress
subtitle used verbatim except "Quite stretches" → "Quiet stretches"
(assumed typo, flagged to him).

**Snapshot truncation extended** to Stress and Breadth (charts + the
index overlay stop at the reading date). Three of eight tabs now
rewind in full; the disclaimer is keyed off that list.

## Canonical list locations (reconciliation)

| List | File | Notes |
|---|---|---|
| All equities (NSE 500) | `data/static/nse500_universe.csv` (500) | authoritative; NSE schema (Company Name, Industry, Symbol, Series, ISIN) |
| Universe snapshots | `nifty50/100/250_universe.csv`, `nifty_smallcap_universe.csv` | current snapshots |
| Effective-dated membership | `data/static/*_membership.csv` (nse500: 534 rows) | survivorship-safe history; use for composites/drill-downs |
| Indices | `data/static/tracked_indices.csv` (40: 4 broad, 3 segment, 4 factor, 22 sectoral, 3 global, 2 commodity, VIX, GS 10YR) | list-driven daily fetch; add a row to track a new index |
| NSE sectoral-index constituents | `data/static/sector_constituents/2026-05/` (12 indices) | many-to-many, partial coverage; quarterly refresh |
| Our sector taxonomy | `data/static/zerodha_sectors.csv` (504 stocks, 30 sectors → 15 super-sectors) | one sector per stock, ~100% coverage; quarterly refresh |
| Index weights | `data/static/index_weights/<INDEX>/2026-04-30.csv` (6 indices) | used by concentration |

**Sector basis ruling: both, with distinct jobs.** NSE sectoral
*indices* (official price series, 2011+ history) power RRG mode 1 —
the market-convention view. Our Zerodha/super-sector taxonomy powers
RRG mode 2 (universe-scoped composites) and ALL stock-level grouping
(lists, screener, drill-downs) — it is the canonical per-stock sector.
The NSE `Industry` column stays as reference metadata only.

## Local dev data refresh

Same-day EOD refresh for local dev = run after market close (bars
final, 16:30 Railway pipeline already ran):

```
.venv/bin/python scripts/run_daily_pipeline.py --with-login --headless --fetch-only
.venv/bin/python scripts/sync_insights_panels.py
```

`--fetch-only` skips portfolio build / DB sync / backup (prod does
those daily anyway); the second command brings the long panels
(`nse500_data_merged/`, `indices_data_full/`) up to date. Append-only
by construction, so never run it mid-session (partial bars would
freeze into the long panels).

## 2026-08-15 — computation audit (Stress + Breadth)

Two read-only agents re-derived every quantity on both tabs from the raw
panels and compared against the live API. **Breadth's backend maths came
back clean** — every metric matched an independent rebuild to 1e-9 on
two universes, atlas band constants match `tasks/breadth_atlas/REPORT.md`
exactly, per-universe caches verified distinct. The defects were on the
as-of path and in presentation.

Fixed:
1. **Overview showed today's data under a historical header.** The
   timeseries endpoints take no date and always return the most recent
   rows; the page never truncated them. On `?date=2020-03-20&universe=
   nifty50` the breadth card read **46%** when the true value was
   **11%** — a 35pp error. Endpoints now accept `date=` and truncate
   server-side; sparklines rewind too.
2. Same defect on Advances/declines, Net new highs, McClellan and
   Concentration detail tabs off the default universe — all truncate now.
3. **`.fillna(0)` on stress components scored "no data" as "maximum
   calm".** Early-2010 dates reachable from the snapshot picker were
   understated by ~18 points. Now renormalised over the components that
   exist; `None` when none do.
4. **A missing percentile was served as `0.0`** and rendered "p0" — a
   confident-looking number for "unknown". Now `None` → em dash.
5. The percentile window is only nominally full early on; the snapshot
   ships `score_percentile_obs` and the card says "vs N sessions so far"
   when the window isn't yet deep.
6. **The stress explainer cited 2008 twice** — the panel starts
   2009-03-05 and contains no 2008 — and claimed 2022 "didn't crack 80"
   when it peaked at 87.6 with 9 days above 80. It also omitted the two
   largest clusters (2011: 69 days, 2016: 16). Rewritten from the panel;
   I verified each figure myself before editing.
7. Dead `StressGauge` component deleted (stale copy, unused).
8. Atlas band constants to full precision (0.222/0.588/0.937).

Open, not fixed:
- Three different band schemes for the same score (docstring 20/40/60/80,
  UI 33/66, explainer 30/60/80). Measured occupancy: <33 = 42.9%,
  33-66 = 46.0%, >66 = 11.1%. Needs one decision, then derive the rest.
- Breadth tiles describe % > 200-DMA while the chart follows the active
  chip; the labels now name the metric but the strip is still static.
- McClellan axis precision collapses (±0.14 range rendered at 1dp).
- Survivorship bias is documented in the engine and the atlas but not
  surfaced on the page.
- `_indices_dir()` duplicated in five modules instead of `_paths.py`.

## 2026-08-20 — stress bands settled

**One scheme: below 35 calm, 35-60 middle ground, above 60 stressed**
(founder). This replaces the three that were in circulation — engine
docstring 20/40/60/80, UI 33/66, explainer 30/60/80.

Defined once as `CALM_BELOW` / `STRESSED_ABOVE` in `stress.py` with a
`stress_band()` classifier, and shipped on the snapshot as `bands` +
`band`. The chart's reference lines, the card label and the explainer
all render from that payload, so the scheme cannot fork again. Spec
tests pin both boundaries and their exact sides — 35 and 60 themselves
are middle ground, so "below 35" and "above 60" read literally.

Occupancy on the 4,262-day panel: **calm 44.6%, middle 38.9%,
stressed 16.6%**. Days above 60 by year: 2011 (140), 2020 (90), 2018
(72), 2013 (71), 2022 (63), 2026 (61 so far), 2016 (52), 2025 (48).

## 2026-08-20 — insights typography: sans + mono only

Founder: the third font (Fraunces, the brand display serif) is
unnecessary and distracting on a dashboard. All 22 `font-serif` usages
under `src/app/insights/**` and `src/components/insights/**` removed;
each carried `font-medium`, bumped to `font-semibold` so headings keep
their step in the hierarchy without the serif's optical weight.

Scope is the dashboard only. Fraunces stays on the brand surfaces —
marketing, library, sign-in, portfolios, account — which is where the
display serif earns its place. `--font-serif` is untouched in
globals.css, so nothing else changes.

Included the `/insights/learn/**` explainer pages: they render inside
the dashboard shell, so a different heading font there would reintroduce
exactly the inconsistency this removes. Say the word if long-form
reading should keep the serif.

Open, deliberately not done: numeric stat values are sans, not mono.
"Sans and mono" could be read as putting the figures in mono, which
would be a bigger visual change than asked for.

## 2026-08-20 — Stress polish + Advances & declines rebuild

**Percentiles are spelled out everywhere.** "p42" reads as a code, not a
position (founder). One `percentileText()` helper renders "Higher than
42%" with the window as its sub, applied to the stress card, the VIX
card, the breadth history tile and the Overview. Two more found while
sweeping: the screener header said "RS %ile", and the stock detail page
rendered "42th percentile" — a broken ordinal, now "Higher than 42% of
NSE 500".

**Stress card**: the band leads at display size (it is the analysis of
the score), the label no longer doubles up as "Stress · Calm", the score
reads "34/100" with no redundant sub, and "from its the past year
closing high" — a mangled string — is now "from the past year's high".

**1Y is the default range on every chart, every tab.** The shared
component defaulted to 3Y with two tabs overriding to 1Y; the default
moved and the overrides are gone.

**A-D line: the founder's question had a real answer.** He asked whether
it depicts percentage or stock count. It was neither cleanly —
`cumulative_ad` is `cumsum(ad_diff_pct)`, a running sum of daily ratios,
i.e. a unitless index. The engine now also publishes the conventional
line: `n_advancing`, `n_declining`, `ad_net_count` and
`cumulative_ad_count` (cumsum of advancers minus decliners, in stocks).
Both forms are chips, stocks first. `_SCHEMA_SENTINEL_COLUMNS` updated
so mtime-fresh caches from older code rebuild.

Also fixed the breadth module docstring, which documented `ad_diff_pct`
as dividing by `#active` when it divides by advancers + decliners
(audit N5) — and chart axis precision, which is now derived from the
series' magnitude rather than fixed at 1dp. That printed the A-D line in
stocks as "-15000.0" and collapsed the McClellan oscillator's entire
±0.14 range onto "0.1 / 0.0 / -0.1" (audit N7).

The A/D tab's cards are readings now, not reference levels: today's
split in stocks, net advances, the line's 20-session move, and the
index's 20-session move with a divergence read.

Open: daily net advances is kept as the third chip. Founder said "maybe
we don't need it" — kept pending a clear call.

## 2026-08-20 — McClellan removed; 52-week highs replaces Net new highs

**McClellan tab deleted** (founder). Tab row, Overview card and detail
view are gone; `/insights/market/mcclellan` now 404s. The engine still
computes `mcclellan_osc` / `mcclellan_sum` — they are cheap, the notes
product may use them, and deleting engine columns is not reversible in
the same easy way a UI route is. The Learn explainer is also kept: it is
correct educational content and reachable from Learn, just not a
dashboard tab. Say if either should go too.

**Net new highs → "52-week highs"** (slug `52-week-highs`). Founder
asked for something more descriptive, suggesting average distance from
the 52-week high. That is the right call and our own research agrees:
the Breadth Atlas found the continuous sibling (avg distance from the
200-DMA) carries the tails far better than the binary count, and the
same asymmetry applies here — a count of names printing a literal new
high is near-zero on most days and then spikes.

New engine columns (TDD): `avg_dist_from_52w_high` (mean of
close/52w-high − 1, always ≤ 0), `pct_within_5pct_of_high`,
`pct_off_20pct_from_high`. `net_new_highs_pct` is kept as the fourth
chip since it remains a standard read.

Sanity check across regimes:

| date | avg dist | within 5% | >20% below |
|---|---|---|---|
| 2020-03-23 (COVID) | -51.2% | 0.0% | 97.2% |
| 2021-10-14 (rally peak) | -7.8% | 45.9% | 9.2% |
| 2026-08-19 (today) | -17.8% | 18.2% | 38.0% |

Worth noting: 38% of the Nifty 500 is more than 20% below its own
52-week high while the index sits near its high — the kind of split the
old count could not show.

**Percentile bands at both extremes** on breadth, A/D and VIX. VIX had
only a p90 and a median; it now uses the same p5 / median / p95 as the
rest, computed from its own history, so a VIX pinned near its floor
reads as a condition rather than an absence. The A/D daily chip keeps
its atlas bands; the two cumulative A-D lines deliberately have none —
percentile bands on a running total describe where the cumsum happens to
have reached, not a comparable level.

Chart axis precision is derived from series magnitude (added with the
A-D work), which is what makes the distance-from-high axis readable at
1dp instead of collapsing.

## 2026-08-21 — density + semantic colour pass (two agent studies)

Two read-only studies commissioned by the founder: one on semantic
colour and icons, one on layout density. Both measured rather than
asserted; I re-verified every number I acted on.

**A live bug the density study found.** The insights topbar had a
`scrollWidth` of 625px in a 390px viewport — **235px of horizontal
scroll on every insights page on mobile**. The right-hand cluster
(universe + snapshot + Today + palette + avatar) needed 369px of a 243px
slot. `overflow-x-clip` on the content div never covered it because the
header is a sibling. Fixed structurally: below `sm` the pickers get their
own full-width row under the mobile nav instead of competing for header
space. Verified 0px overflow, `scrollWidth === innerWidth`.

**Density.** Hairline grids (`CardGrid`: `gap-px` over a `bg-border`
parent) replace gap-separated cards, cells lose their own chrome, mobile
goes 2-up rather than 1-up, and the app padding scale tightens. Measured:

| surface | before | after |
|---|---|---|
| Overview @390 | 2943px (3.49 screens) | **1870 (2.22)** |
| Overview @1440 | 1432 (1.59) | **1126 (1.25)** |

Reclaimed space goes into **data ink, not whitespace** — desktop charts
grow 320 → 400px; mobile charts drop to 260 (the study's floor is 240).
Chip tap targets **grew** on mobile (25 → 32px) against the density
grain, deliberately.

**The app scale is now named**, not scattered: `--app-pad/-lg`,
`--app-gap/-lg` on `.mw-app` in globals.css. The dashboard forking from
the marketing scale is a founder decision; naming it means a future
design pass retunes from one place rather than hunting ~40 paddings.
This matters because `design_studies_clay` is live on another branch.

**Semantic colour.** The regime label had **five implementations** and
two disagreed on DRIFT (Overview said foreground, ui.tsx said muted).
Now one `REGIME_CSS_VAR` + `RegimeChip` in ui.tsx; the other four are
deleted. The two headline regime tiles finally carry the swatch their
own "Recent regimes" list already had.

Icons where they earn it: the three Overview section headers reuse the
sidebar's own glyph in an accent chip, and each Market Pulse tab gets
one. Deliberately NOT per regime state — that lexicon is
compliance-controlled and a glyph per state is editorial commentary.

The divergence readout — the most analytical sentence on Breadth and
A/D — was rendering as the page's smallest, faintest text in the tile
`sub` slot. Promoted to its own line with `Split`/`Equal` and
`--chart-3`. On `--chart-3` rather than warning-ochre on purpose: a
narrowing tape is worth noticing, not an alarm. The agreeing/diverging
state is now an explicit flag rather than string-matching the sentence.

**Where colour was refused**, per the study and the standing "descriptive,
never a signal" rule: extension bands (a red "Very high" is a sell call
in everything but name), the four stress components, new-high/new-low
counts, and the stress band on a green axis (painting "Calm" green reads
as "safe to buy" — it uses the calm→warning axis instead).

Standing rule from the measurements: **never put token-coloured text on
a tint of the same token** — positive-on-positive/10 is 4.16, warning
on warning/10 is 4.06, both below AA.

Open from the studies, not done: replacing the Overview cards' prose
`foot` with a data line (`55% · +2pp 20d · 43rd pctile`) — denser *and*
more informative, but it needs `pctRank`/`changeOver` lifted out of the
detail page into a shared helper; hiding `InsightsMobileNav` on
`/insights/market/*` to kill 104px of stacked nav chrome; and a bottom
nav bar as the better long-term mobile answer.

## 2026-08-21 — A-D chart presentation: founder picked E + F

Ran six presentation experiments for the Advances & declines chart
(`experiments/ad_chart_views.html`, self-contained, real engine data
through 2026-08-19; editable source `experiments/ad_views_template.html`
— rebuild by splicing the lightweight-charts standalone bundle + data
JSON over the `/*__LIB__*/` and `/*__DATA__*/` markers). Informed by a
signed-in TradingView session: their ADL always gets its own pane below
price (shared time axis, per-pane legends); overlays they DO allow get
a visible left % axis; daily series render as sign-coloured columns.

**Founder verdict: E and F look the best.**

- **E** — index overlay rebased to % from the left edge of the visible
  window on a VISIBLE left axis (readable level, 0% line = "flat since
  window start"). A-D keeps the right axis.
- **F** — A-D drawn as a BaselineSeries anchored at the first visible
  day: green above / red below answers "net breadth up over this
  window?" by colour alone.
- Both got pan/zoom in the experiment (wheel/pinch zoom, drag pan,
  axis drag/double-click reset) with the rebase/anchor re-computed on
  `subscribeVisibleLogicalRangeChange` — the anchor follows the window
  as you scroll. lightweight-charts v5 supports all of it natively;
  v5 panes (`addSeries(..., paneIndex)`) remain available if B's
  two-pane layout is ever wanted.

Not yet implemented in production `TimeseriesChart` — that's the next
step when the founder asks: visible-left-axis overlay + baseline mode
+ opt-in pan/zoom (keep `handleScroll.mouseWheel: false` so the page
still scrolls; consider `fixLeftEdge/fixRightEdge`).

**Implemented same day** on the Advances & declines tab only (founder:
"implement on one tab and then we can see how it looks"; fixRightEdge
explicitly approved). `TimeseriesChart` gained opt-in `baseline`,
`overlayAxis="left"` and `interactive` props (defaults preserve every
other tab); `MetricExplorer` passes them through; the two cumulative
A-D variants set `baseline: true`, the daily variant stays a line.
Interactive charts keep the full fetched history and the range pills
set the initial visible window (`setVisibleLogicalRange`), edges fixed
both sides, `handleScroll.mouseWheel: false` so the page still
scrolls. Verified in a signed-in browser at 1440x900 and 390x844:
baseline anchor + overlay rebase follow pan/zoom; Breadth and the
other tabs unchanged; `npm run build` + eslint clean.

**2026-08-22 amendment — anchor line, not baseline fill.** Founder: the
green-above/red-below fill "keeps redrawing as the zeroline changes...
especially busy with the overlay". The `baseline` prop became `anchor`:
same dashed start-level line, same re-anchor-on-pan, but the series
stays the ordinary single-colour area. BaselineSeries usage removed.

**2026-08-22 — A-D line negativity audited, computation confirmed.**
Founder asked why the NSE 500 cumulative A-D count sits near −21k.
Verified three ways: (1) independent recompute of 2026-08-19 straight
from the raw price CSVs matches the panel exactly (137 adv / 362 dec /
1 flat of 500); (2) only 21 stock-days in 17 years show < −40% moves
(possible unadjusted corporate actions, ECLERX worst at 4) — immaterial
to a −21,026 total; (3) the drift is genuine: 49.29% of stock-moves are
advances vs 50.71% declines, mean −4.9 net/day since 2009. Count-based
A-D lines on pure-equity universes drift negative because the median
stock has slightly more down days — gains come concentrated in fewer,
bigger up-days. Big negative years line up with known regimes (2011
−5.2k, 2018 −5.2k midcap bear while Nifty 50 was up, 2019 −4.3k,
2025 −3.8k). Survivorship bias in the current-membership panel pushes
the line UP if anything, so the real historical universe would be more
negative still. This is exactly why the level is meaningless and the
anchor line + direction is the read.
