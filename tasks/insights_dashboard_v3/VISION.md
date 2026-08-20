# Marketworks Terminal — Pro/Max dashboard experiment (insights_dashboard_v3)

Status: exploration only. No code yet. PLAN.md/TASKS.md follow if the
founder greenlights direction. Screenshots of the reference in
`evidence/`.

## What was studied

Kimi showcase "GMT://TERMINAL — Global Market Monitor"
(https://www.kimi.ai/showcases/websites/gmt-terminal-market-monitor,
direct app: https://s4ibp54hd7bwq.kimi.page/?id=2082748652610740224).
A single-page Bloomberg-style terminal running on labeled offline demo
fixtures. Explored live via Playwright, including edit mode, widget
picker, layout presets, and the tile inspector.

### Feature inventory of the reference

1. **Command bar** — product mark, dual clock (local + UTC), DEMO DATA
   badge, connection state ("CONN: DEMO/OFFLINE · live unconfigured"),
   current FOCUS ticker, inline keyboard legend
   (`[E]dit [A]dd [R]eset [D]ata [T]ape [Esc]`), four layout presets
   (GLB / EQ / MET / NWS), EDIT, +WIDGET, RESET, POP, DATA buttons.
2. **Index tape** — auto-scrolling marquee of global indices + gold +
   WTI + DXY;每 chip shows last/chg/chg%/OPEN-CLOSED state; pausable;
   chips are clickable buttons.
3. **Widget grid (9 widgets, numbered like Bloomberg panels)**:
   - 01 GLOBAL TICKER — dense indices table (last/chg/chg%/state/src/as-of)
   - 02 STOCK TRACKING — treemap heatmap, sector-grouped; filter chips
     (ALL/sector), metric toggle (|CHG%| / MKT CAP / TURNOVER), ticker
     search; tile size = metric, tile color = direction × intensity
   - 03 MARKET BREADTH — advancers/decliners/unchanged, A/D ratio,
     top gainer/loser, advance-decline bar
   - 04 SECTOR INTRADAY (normalized) — rebased multi-line sector chart +
     per-sector avg-chg bars + weighting table
   - 05 NEWS WIRE — timestamped headline stream with category filter
     chips (AI/TECH/ENERGY/FINANCE/MACRO/METALS), grep box, pause;
     honestly banner-labeled "ALL HEADLINES ARE ILLUSTRATIVE FIXTURES"
   - 06 FOCUS · 60 TRADING SESSIONS — OHLC header strip, line chart with
     crosshair + inspector pinning, volume bars, session-count footnote
   - 07 PRECIOUS METALS MONITOR — four spot sparkline tiles + derived
     ratios/spreads (gold/silver ratio, AU-PT spread) + 60-session chart
   - 08 MARKET PULSE · GLOBAL SESSION CLOCK — big live clock, per-exchange
     session table (local time, session windows, state, next event
     countdown), horizontal session-band timeline, display-TZ selector
   - 09 GLOBAL INDEX MAP — indices grouped by region (Americas/Europe/APAC)
4. **Panel chrome** — every panel: numbered badge, title, as-of stamp +
   DEMO tag, pin / minimize / maximize / close controls.
5. **Edit mode** — drag + corner-resize every panel; +WIDGET picker
   doubles as restore-for-deleted; RESET returns to preset; POP opens a
   panel in its own window.
6. **Inspector rail** — clicking any heatmap tile (or pinning a
   crosshair) opens a right drawer: quote block (last/chg/OHLC/volume/
   mkt cap/turnover/currency) **plus a PROVENANCE block** (adapter,
   source, mode, as-of, latency, error, fallback, data conventions) and
   the list of available fields.
7. **Honesty discipline** — every number carries as-of; demo data is
   labeled at the command bar, per panel, per widget, and in the
   inspector. Nothing pretends to be live.

## What we already have that maps onto it

The insights dashboard (branch `insights_dashboard_v2`) already ships
the *analytics*; the terminal is a different *shell* over the same
engines:

| GMT widget | Marketworks equivalent (existing) |
|---|---|
| 01 Global ticker | `/index/timeseries?universe=` — Nifty 50/100/250/500 + India VIX |
| 02 Heatmap | movers + universe cross-section (needs treemap component) |
| 03 Market breadth | breadth panel: advancers/decliners, % above 21/50/100/200-DMA, net new highs, McClellan |
| 04 Sector normalized | sectors RS data (RS tornado today; RRG spec pending D3) |
| 05 News wire | **Signals wire** — regime flips, stress band crossings, list entries/exits, detector events (no fake news; our events are real engine output) |
| 06 Focus chart | Regime tab chart (lightweight-charts, line/candles, regime tint, crosshair) |
| 07 Metals monitor | closest analog: India VIX + stress composite tiles (or drop) |
| 08 Session clock | NSE session clock + pipeline freshness (`/api/freshness`) |
| 09 Index map | universes summary table |
| Inspector provenance | as-of snapshot stamps + freshness monitor already exist; surface them per-panel |
| DEMO badge honesty | our EOD "as-of <date> close" posture — same discipline, real reason |

Also directly reusable: `?date=` rewind (terminal-wide as-of mode),
universe selector, `TimeseriesChart` + `indexOverlay()`, stat-strip and
learn-panel components, Supabase auth + entitlements_v1 for gating.

## The vision — "Marketworks Terminal"

A Pro/Max tier surface for power users: one dense, keyboard-driven,
multi-panel screen over the exact same insight engines — no new
analytics, no new claims, just a new shell with higher information
density and user-composable layout.

- **Same functionality, recomposed**: every Market Pulse tab becomes a
  widget; Overview's mission-control cards become small stat widgets;
  movers/lists become a wire + heatmap.
- **Layout presets** instead of GLB/EQ/MET/NWS: e.g. MKT (regime +
  stress + breadth + tape), BRD (breadth family), SEC (sectors/RS),
  LST (stock lists + heatmap + focus chart).
- **Edit mode + widget picker + per-user layout persistence**
  (localStorage first, DB later).
- **Inspector rail** on any stock/sector click: quote, RS percentile,
  DMA distances, which lists it's in, provenance (engine, as-of,
  universe, data conventions).
- **Command bar**: focus-ticker search, universe selector, `?date=`
  rewind surfaced as an explicit AS-OF control, keyboard shortcuts.
- **Honest by construction**: EOD data labeled per panel ("as-of
  2026-08-13 close"), freshness state in the command bar; the signals
  wire only carries engine events. (Intraday later = Slice 5 posture C.)
- **Skin**: deliberate terminal aesthetic (dark, mono, amber/green/red)
  as a distinct theme — per founder process, Pencil mock + sign-off
  BEFORE component code.
- **Gating**: admin-only behind the existing role check first; then a
  `pro`/`max` entitlement when entitlements_v1 lands.

## Founder decisions (2026-08-20)

- **Name: "Terminal"** — confirmed.
- **Desktop only** — confirmed. Gate below ~1100px; small screens fall
  back to the basic insights dashboard.
- **Shell toggle in profile settings** — power users flip between the
  basic dashboard and the terminal shell per their profile; it is a
  presentation choice, not a separate data product.
- **Brand colors, not a GMT copy** — the aesthetic is approved but the
  skin must read as a Marketworks product. Mock reskinned onto the
  production **Midnight** tokens (`kite-dashboard/src/styles/
  marketworks/tokens.css` `.dark` block): page `#0C1219`, panel/card
  `#17202C`, border `#2C3947`, ink `#E9EEF4`, muted `#8F9AA8`;
  accent = **brand marigold `#E8A33D`** (command bar, panel numbers,
  titles, symbols); up/down = production finance-direction pair
  `--chart-positive #57A876` / `--chart-negative #D07162`; interactive
  blue = Midnight `--primary #58A6E8`. Every colored value keeps
  ▲/▼ + signed number (the non-color channel — required, since the
  green/red pair alone is not CVD-distinct).
- **Keyboard shortcuts + slash command palette** — planned feature
  (founder ask): `/` opens a fuzzy command bar for stock lookup
  (→ focus chart / inspector / screener) and go-to-panel or actions
  (`/regime`, `/breadth n250`, `/date 2026-06-30`, `/universe n100`,
  `/shell`). Mocked as an overlay in the P0 file (toggle
  `body.show-cmdk`); see `evidence/mw-terminal-brand-cmdk.png`.
- **P0 is a hand-built HTML mock, not Pencil** — done:
  `mock/terminal_mock.html` (open directly in a browser; fully static,
  single file). Branded render: `evidence/mw-terminal-brand-final.png`
  (pre-rebrand GMT-amber version kept as
  `evidence/mw-terminal-mock-final.png` for comparison).
  Every value on it is an illustrative fixture and the page says so in
  a top banner, per-panel MOCK tags, and the inspector's
  `mode: MOCK FIXTURE` row.

### Suggested phasing (if greenlit)

1. **P0 mock** — DONE as static HTML (see above); founder
   sign-off on direction.
2. **P1 static grid** — fixed layout, 6 widgets fed by existing
   endpoints (tape, regime chart, stress, breadth, sector RS, lists).
   No edit mode. Admin-gated route `/terminal`.
3. **P2 composable** — edit mode (drag/resize), widget picker, presets,
   layout persistence.
4. **P3 depth** — inspector rail, signals wire, session/freshness
   clock, and the **keyboard layer + command palette** (its own task):
   global shortcut map (`/` command, E/A/U/D, Esc, panel focus cycling)
   plus the slash palette — fuzzy search over symbols, names, panels,
   and commands; stock hits open focus/inspector/screener; command hits
   navigate or act (`/regime`, `/breadth <universe>`, `/date <d>`,
   `/universe <u>`, `/shell`). Reuses the terminal's existing search
   endpoints; no new analytics.
5. **P4 polish** — pop-out panels, heatmap treemap (D3 — shared
   dependency with RRG Slice 3), maybe multi-focus charts.

### Open questions for the founder

- Tier/pricing: is Terminal an entitlement (pro/max) or free for all
  power users once out of beta?
- D3 adoption decision (blocks both RRG and the treemap heatmap).

Resolved: name is **Terminal**; aesthetic approved, reskinned onto
brand Midnight tokens + marigold; desktop-only (gate ~1100px);
terminal sits beside the basic dashboard behind a profile-settings
shell toggle — shared panel cores keep the maintenance surface single;
keyboard layer + slash command palette is a planned task (P3).
