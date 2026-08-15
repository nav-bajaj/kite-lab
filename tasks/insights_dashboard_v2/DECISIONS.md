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

Still unverified: the *writing* half. Leaving a comment needs the
founder's own Vercel session in his browser, which the agent cannot
exercise. One test comment settles it. The fallback if it disappoints
stays on the table — a local annotation overlay writing notes to a
JSON file in the repo, fully offline, no account involved.

Also fixed while here: `REVALIDATE_SECONDS` is now 0 in development.
The 15-minute fetch cache was serving `/reading` responses captured
before a backend field existed, which is what made the Participation
tile look empty on non-default universes.

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
