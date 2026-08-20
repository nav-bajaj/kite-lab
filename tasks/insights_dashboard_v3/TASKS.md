# TASKS — insights_dashboard_v3 ("Terminal")

Phases P1+ are parked until `insights_dashboard_v2` is final (see
PLAN.md sequencing rule). Owners: 👤 founder · 🤖 agent.

## P0 — vision + mock — DONE 2026-08-20

- [x] 🤖 Explore GMT://TERMINAL reference via Playwright; feature
      inventory + widget→endpoint mapping (VISION.md)
- [x] 🤖 Static HTML mock, 9 widgets + inspector rail + command bar +
      tape (`mock/terminal_mock.html`)
- [x] 👤 Aesthetic sign-off; name = **Terminal**
- [x] 🤖 Reskin onto brand Midnight tokens + marigold (founder: must
      look like a Marketworks product, not a GMT copy)
- [x] 🤖 Command palette mocked (`/` overlay; `body.show-cmdk`)
- [x] 👤 Decisions: desktop-only ~1100px gate; profile-settings shell
      toggle BASIC | TERMINAL

## P1 — static grid (after v2 final)

- [ ] 🤖 Re-derive widget catalog from v2's FINAL shipped tabs
- [ ] 🤖 Extract shared panel cores so basic tabs + Terminal widgets
      render the same components [risk: refactor of live v2 pages]
- [ ] 🤖 `/terminal` route: fixed 3-col grid, 6 core widgets (tape,
      regime, stress, breadth, sector RS, lists) on existing endpoints
- [ ] 🤖 Desktop gate + admin-only access first
- [ ] 👤 Review pass on-page (Vercel Toolbar flow, as in v2)

## P2 — composable shell

- [ ] 🤖 Edit mode: drag + resize panels
- [ ] 🤖 Widget picker (add/remove/restore) + layout presets
      (MKT/BRD/SEC/LST) + RESET
- [ ] 🤖 Layout persistence (localStorage first; DB column later)
- [ ] 🤖 Profile-settings shell toggle (BASIC | TERMINAL) wired to
      routing [risk: interacts with auth_stack_v2 profile model]

## P3 — depth: inspector, wire, keyboard + command palette

- [ ] 🤖 Inspector rail: quote + momentum profile + list membership +
      provenance block (engine, as-of, universe file, adjustments)
- [ ] 🤖 Signals wire: engine-event feed (regime flips, stress band
      crossings, breadth crossings, list entries/exits) + category
      filters + grep [risk: needs event persistence — daily
      cross-section diffs; align with v2 Slice 4 detectors]
- [ ] 🤖 **Keyboard layer + slash command palette** (founder ask,
      2026-08-20): global shortcut map (`/`, E/A/U/D, Esc, panel focus
      cycling); palette = fuzzy search over symbols, names, panels,
      commands; stock hits → focus chart / inspector / screener;
      command grammar `/regime`, `/breadth <universe>`,
      `/date <yyyy-mm-dd>` (as-of rewind), `/universe <u>`, `/shell`
- [ ] 🤖 Session/freshness clock widget (NSE hours + /api/freshness)

## P4 — polish

- [ ] 🤖 Pop-out panels (own window)
- [ ] 🤖 Treemap heatmap widget [blocked: D3 decision, shared with v2
      RRG Slice 3]
- [ ] 👤 Tier decision: entitlement (pro/max via entitlements_v1) vs
      free power-user option
- [ ] 🤖 Compliance pass on all Terminal copy (v2 D4 lexicon)
