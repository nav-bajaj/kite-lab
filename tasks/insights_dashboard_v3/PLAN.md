# PLAN — insights_dashboard_v3 ("Terminal")

Opened 2026-08-20. Status: planned — P0 (vision + HTML mock) is done
and signed off; the build is deliberately PARKED until
`insights_dashboard_v2` completes. Terminal is a shell over the final
dashboard's feature set, so it starts from v2's finished state, not in
parallel with it.

## Why

Power users want a Bloomberg-style, high-density, keyboard-driven
surface. The insights dashboard (v2) optimises for guided reading —
one indicator at a time with learn panels. Terminal presents the same
engines all at once: composable widget grid, focus chart, signals
wire, inspector rail. It is a **presentation shell, not a new data
product** — no new analytics, no new claims, every widget maps to an
existing v2 endpoint.

Reference studied: Kimi "GMT://TERMINAL" showcase (see VISION.md for
the full feature inventory and the widget-to-endpoint mapping).

## Outcome

A `/terminal` route in kite-dashboard, desktop-only (gate ~1100px),
reachable via a **profile-settings shell toggle** (BASIC | TERMINAL).
Clients who flip the toggle land on Terminal instead of the basic
insights dashboard; same auth, same universe access rules, same data.

Decisions already made (founder, 2026-08-20 — detail in VISION.md):

- Name: **Terminal**.
- Skin: terminal aesthetic on **brand Midnight tokens** — surfaces
  `#0C1219`/`#17202C`/`#2C3947`, accent brand marigold `#E8A33D`,
  up/down = `--chart-positive`/`--chart-negative`, interactive blue
  `--primary`. Every colored value carries ▲/▼ + signed number
  (required: the green/red pair alone is not CVD-distinct).
- Keyboard layer + `/` slash command palette (stock lookup, go-to
  panel, actions) is in scope as its own task.
- Honesty discipline: per-panel as-of stamps, pipeline freshness in
  the command bar, signals wire carries engine events only — never
  external news.

## Scope boundary

IN: widget grid + panel chrome, layout presets, edit mode + layout
persistence, inspector rail, signals wire (engine events), keyboard
layer + command palette, session/freshness clock, profile shell
toggle, entitlement gating hook.

OUT: any new indicator or analytic; intraday data (that is v2 Slice 5
and lands there first); mobile; treemap heatmap and RRG until the D3
decision (shared dependency, decided in v2's Slice 3).

## Critical files

- `tasks/insights_dashboard_v3/VISION.md` — exploration findings,
  widget→endpoint mapping, decisions log.
- `tasks/insights_dashboard_v3/mock/terminal_mock.html` — P0 mock
  (static single file; open in a browser; `body.show-cmdk` shows the
  command palette). All values are labeled illustrative fixtures.
- `tasks/insights_dashboard_v3/evidence/` — GMT reference captures +
  mock renders.
- `kite-dashboard/src/styles/marketworks/tokens.css` — Midnight token
  source the skin maps onto.
- `tasks/insights_dashboard_v2/STATE.md` — the dashboard whose final
  feature set Terminal will mirror.

## Sequencing rule

Do not start P1 while v2's indicator deep-dive / RRG / Stock Lists /
intraday slices are still moving. When v2 is declared final, re-derive
the widget catalog from its shipped tabs, then build. Panel internals
should be extracted into shared components so the basic dashboard and
Terminal render the same cores (single maintenance surface).
