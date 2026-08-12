# design.md — Marketworks brand system: "The Document of Record"

Status: experimental proposal, branch `design_reset`, 2026-08-12.
Written unattended at the founder's request, from scratch, after 22
loops of prior study converged nowhere the founder felt sure of.
The built proof is `tasks/design_reset/home.html` (open it in a
browser). This file documents the system the way it was BUILT, not
the way it was imagined; every rule below is live on that page.

Provenance note (hard rule honored): every performance figure on the
mock traces to `docs/portfolios.md`; the chart is real NSE index data
(Nifty500 Momentum 50 vs Nifty 500, month-end closes, Jan 2020 = 100,
from `~/Documents/stock_data/indices_data_full/`). The single
placeholder on the page is the bracketed regulatory line in the
footer, which only the founder can supply.

---

## 1 · The idea

**Marketworks is a document of record, not a pitch.**

The identity is drawn from the artifact where financial trust has
physically lived in India for a century: the security-printed
instrument — share certificates, contract notes, cheque paper,
allotment letters. Guilloche engraving, rule-lined ledgers, serial
numbers, stamps, seals, microtype disclosures. Every Indian with a
demat account receives this grammar in their inbox; every
institution they trust (RBI, the exchanges, their bank) speaks it.

Why it fits this product and no competitor can wear it honestly:
Marketworks' positioning IS documentary — out-of-sample validation,
published drawdowns, a ledger of rejected experiments, a fixed daily
cadence. A document of record makes the product's honesty visible as
form. Finfluencers cannot copy it (their grammar is urgency), and
fintech apps cannot copy it (their grammar is friction-free
lightness).

What it deliberately refuses:
- the **dark-terminal glow** (near-black + neon data viz) — the
  quant-category default;
- the **cream-editorial serif** restraint — the AI-default lane the
  previous brand systems (mist/lichen, Clay-vivid) already orbit;
- finfluencer urgency, SaaS gradients, stock photography (standing
  anti-references, carried forward).

Register for the 22–45 Indian audience: institutional weight worn
lightly. The page should feel like the most credible document they
have ever been handed by a finance brand — and still read on a phone
in two minutes.

## 2 · Color — "intaglio on cheque paper"

Ink on security paper. One committed dark field per page. One red
action.

| Token | Value | Role |
|---|---|---|
| `--paper` | `#F2F4F0` | Ground. Cool cheque-paper, faintly green-grey. Never warm cream, never pure white. |
| `--paper-high` | `#F9FAF8` | Raised sheet: exhibits, ledgers sit on this. |
| `--ink` | `#17211B` | Body ink. Green-black, engraving-toned. |
| `--ink-2` | `#46554C` | Secondary ink (≥4.5:1 on paper). |
| `--ink-3` | `#5E6D64` | Muted ink: captions, microtype (≥4.5:1). |
| `--rule` | `#C9D2CA` | Hairlines: table rules, section dividers. |
| `--intaglio` | `#0E3B2E` | The deep field. One full-bleed region per page (the access band); also the seal/lathe-work ink. |
| `--intaglio-ink` | `#1E7A4A` | The brand's line ink: momentum series, clause numbers, rule accents. |
| `--cheque-blue` | `#3D5FC9` | Second data ink (benchmark series). Data only, never UI. |
| `--seal-red` | `#C03A20` | The franking stamp: primary CTA, stamps. ONE red action per viewport. |
| `--on-deep` / `--on-deep-2` | `#EAF1EC` / `#A9C4B4` | Text on the intaglio field. Secondary is tinted from the hue, never gray. |

Rules, as built:
- Color strategy is **Committed**: the intaglio family carries the
  page; the red exists only where the reader can act (or where a
  stamp certifies/rejects). If red appears twice in one viewport,
  one of them is wrong.
- Data inks and UI inks stay separate. `--cheque-blue` never
  becomes a button; `--seal-red` never becomes a data series.
- Chart palette `#1E7A4A` + `#3D5FC9` on `#F2F4F0` is
  validator-passed (CVD ΔE 21.6 deutan, normal 23.6, contrast ≥3:1
  — dataviz six-checks). Re-run the validator before adding a third
  series.
- Losses print in the same ink as gains. No red negative numbers:
  the page says "drawdowns printed in the same ink as returns" and
  the table obeys it. (Semantic red/green stays available inside the
  product dashboard; this is a marketing-surface rule.)

## 3 · Typography — three instruments

| Face | Weight | Role |
|---|---|---|
| **Rozha One** (Indian Type Foundry, Google Fonts) | 400 only | The engraved plate: masthead wordmark, H1/H2 document titles. High-contrast, unmistakably of Indian print. Never below 26px; never for UI. |
| **Public Sans** | 400 / 500 / 600 | The typewriter of official documents: body, UI, table text, buttons. |
| **Fragment Mono** | 400 | The serial number: doc refs, clause numbers, figures, axis labels, microtype stamps. Always `tabular-nums` for figures. |

Scale as built: H1 `clamp(42px, 6.2vw, 78px)` / 1.04; section titles
`clamp(26px, 3.2vw, 38px)`; lede 18/1.6; body 15–16/1.55; captions
12.5; microtype 12. Weight ceiling 600. Tracking near-zero (Rozha
One carries its own tension; do not track it tight).

No eyebrows. The old `eyebrow` slot is dead; its job is done by the
document grammar itself (clause numbers in the section rule-line,
italic marginal notes, the deed line inside the lede).

## 4 · The document grammar (layout system)

- **The frame.** Every page sits inside a double rule (1.5px border +
  1px offset outline, 14px viewport margin; 8px on phones). The
  frame is the brand's first signal — content lives ON a document.
- **Masthead → lathe band → doc-ref.** Wordmark + contents + one
  bordered CTA; a 26px generative guilloche band; a mono reference
  row (`Research note Nº MW/…`, market, issue date). The doc-ref is
  real metadata, updated per issue — never decoration.
- **Sections are clauses and exhibits.** Every section head is a
  full-width rule-to-rule row: mono clause number (`CLAUSE I`,
  `EXHIBIT A`, `SCHEDULE A`) + Rozha title + italic marginal note.
  The numbering is the page's actual reading order (it repeats in
  the footer contents); it is structure, not ornament.
- **Ledgers, not cards.** Tabular content renders as rule-lined
  tables on the raised sheet with mono figures. On phones the ledger
  stacks into labeled entries (data-label pattern), never into
  icon-cards.
- **Stamps certify, they don't decorate.** The rotated double-border
  mono stamp appears only where it states a checkable fact
  ("OM25 · TL25 validated out-of-sample 2017–2026", "REJECTED").
  A stamp that states a mood is banned.
- **The deep field closes.** One full-bleed intaglio band near the
  end (the access offer) — the single dark moment, like the
  signature block of a deed. Paper-colored CTA on it.
- **Disclosures are content.** The footer is a microtype disclosure
  block written honestly (backtest basis, slippage, market risk).
  The regulatory line is a bracketed placeholder until the founder
  supplies it — never invent it.
- Max content width 1080px; section padding ≥52px top / 72px bottom
  desktop, tighter on phone. Whitespace stays generous — documents
  breathe in margins, not in decoration.

## 5 · Line-work (the ornament system)

All ornament is **generated line geometry**, never raster texture,
never CSS gradients:

- **The seal**: superposed two-frequency rose curves
  (`r(θ) = base + a₁sin(n₁θ) + a₂sin(n₂θ)`, paired with a
  phase-offset ghost), ringed by mono ring-text: RULES · EVIDENCE ·
  DISCIPLINE · MARKETWORKS. This is the brand mark of this system —
  a machine-turned rosette no two competitors would generate alike.
  Implementation in `home.html` (`rosette()` / `drawSeal()`).
- **The lathe band**: three phase-shifted interfering sine strokes
  under the masthead.
- **Engraved area fill**: charts fill under the primary series with
  a 45° fine-line hatch pattern at low opacity, not a gradient.
- Stroke discipline: ornament strokes 0.5–0.7px at rest, opacity
  .35–.85; ink color only. Ornament never sits under body text.

## 6 · Data visualization

- Real data or no chart. A labeled-synthetic shape is acceptable
  only when visibly captioned as illustrative; invented numbers
  never. (The mock ships real NSE index series with the source and
  method in the caption.)
- Every chart: recessive dotted grid, mono axis labels, ≤2–3 series,
  direct end-labels + legend, crosshair + tooltip on hover, a
  "view the underlying table" disclosure for accessibility, single
  y-axis always.
- Figures in text and tables: Fragment Mono, tabular. Every number
  carries its context (period, universe, net-of-slippage) in the
  same block — a stat without a caption is a defect.
- Motion: ONE authored moment per page. Here: the exhibit line
  draws on (1.6s expo-out) when scrolled into view, with a 4s
  fallback and full `prefers-reduced-motion` bypass. Nothing else
  animates except hovers ≤120ms.

## 7 · Voice on the surface

Calm, sharp, deed-like. The confirmed brand voice
("probabilistic-not-predictive") written into document language:

- Certify, don't promise: "This document records a process, not a
  promise."
- Print the losses in headline positions; honesty is the
  differentiator ("The rejected ledger", "Risk, in plain terms",
  drawdowns beside CAGRs at equal weight).
- No urgency mechanics, no "last chance", no animated counters, no
  exclamation marks. CTAs name the action plainly: "Request beta
  access."
- Wordmark stays lowercase `marketworks.` (now set in Rozha One);
  the trailing full stop is the wordmark's period — a sentence that
  ends, like a document does.

## 8 · Accessibility & performance floor

Body inks ≥4.5:1 on their grounds (validated); focus-visible rings
(2px seal-red, offset 2); chart has aria description + table
fallback; `prefers-reduced-motion` kills scroll behavior, draw-on,
and transitions; semantic heading order h1→h2→h3; the page is a
single HTML file, system-free, no framework, fonts via Google Fonts
(self-host via `next/font` when productionized).

## 9 · Where this system would go next (not built)

- **Microprint rules**: replace key hairlines with genuine repeating
  microtype (a security-print signature the mock approximates with
  plain rules). Plate-texture ground for the intaglio band.
- **Stamped-impression CTA**: give the primary action a pressed-ink
  treatment so the world's stamp grammar lands on the one element
  that matters.
- **Dashboard translation**: paper/ink tokens map to a light
  operate-surface; the intaglio field becomes the authenticated
  header; semantic gain/loss colors return inside data regions.
  Dark mode = "the night ledger" (paper and ink invert to deep
  green-black + pale ink) — design it, don't flip it.
- **Devanagari**: Rozha One ships a companion Devanagari — this
  system is Hindi-ready by construction, unlike every previous
  Marketworks system. Worth naming as a strategic advantage.
- Social templates: the certificate crop (frame corner + seal +
  one figure with caption) is a natural 1080×1350 unit.

## 10 · Relationship to the incumbent systems

This replaces, on this branch only: the mist/lichen editorial system
(`~/marketworks-design/DESIGN.md`) and the Clay-vivid two-theme
study (`design_studies_clay`). Both remain untouched on their own
branches. Universe IDs, product copy discipline, the no-fabrication
rule, and the lowercase wordmark carry forward. If the founder
adopts this direction, the migration order is: tokens →
marketing surfaces → social templates → dashboard; and
`~/marketworks-design` gets a new major version rather than an edit.
