# design_reset — variant record

Three from-scratch identities over identical product truth. Same real
NSE chart (Nifty500 Momentum 50 vs Nifty 500, Jan 2020 = 100), same
portfolio record from `docs/portfolios.md`, same real signal ranks of
12 May 2026, same eight-beat story (hero → rules → premium chart →
portfolios → rejected ledger → risk → access → disclosures). The
worlds differ; the information architecture is deliberately held
constant so the founder compares identity, not content.

Chooser: `index.html`. Serve the folder and open it
(`python3 -m http.server 4180` → http://localhost:4180/).

## Variant 1 — The Document of Record (`home.html` + `design.md`)

Indian security-print instrument. Cheque-paper ground `#F2F4F0`,
double-rule engraved frame, generative guilloche seal, intaglio green
`#0E3B2E`/`#1E7A4A`, franking-stamp red `#C03A20`. Rozha One ·
Public Sans · Fragment Mono. Fully documented in `design.md`.
Finish-review disposition: ship.

## Variant 2 — Spectrum Ledger (`home2.html`)

Founder-pinned brief: "ramp.com but with more color." The Ramp
grammar kept — one grotesk (Hanken Grotesk + Spline Sans Mono
figures), sticky nav with pill CTAs, product-proof hero (the real
Core Momentum signal board of 12 May 2026 as a white UI card on a
saturated blue stage), stat strip, alternating sections, black
contrast band, big CTA band — but the ivory monochrome replaced by a
committed four-hue system doing structural work:

| Role | Value | Where |
|---|---|---|
| bone ground | `#F6F4EF` | page (Ramp's own signature, pinned) |
| electric blue | `#2244EE` | primary, hero stage, momentum series |
| coral | `#E8501F` | second hue, benchmark series |
| amber | `#C77E12` | third hue (replaced violet — AI-purple tell) |
| lime | `#D7F03C` | action color on dark; access band |

Each hue ships a tint + deep-ink pair; mechanism rows and the four
portfolio cards rotate through them. Chart palette validator-passed
(blue/coral on bone). Known accepted gap: mobile nav links hidden
with no menu (footer carries the anchors); prototype scope.

## Variant 3 — The Ring (`home3.html`)

Assigned by concept-seed roll 95734758: Indian trading-floor
heritage. Slate chalkboard `#161C18`, warm chalk `#EDE7D6`, brass
rail/plaque `#C9A24B` (single metal moment, real turbulence grain),
cream ticker tape with torn clip-path edges carrying the real 12 May
2026 ranks. Besley (signage display) · Archivo (body) · Courier
Prime (tape/figures). Chalk is rendered material, not just color:
`#chalkstroke` displacement on headline underline, rule underlines,
strikethroughs, and the chart lines; `#dustgrain` on the exhibit
board. Chart inks validator-passed for the dark band: yellow-chalk
`#AD861F` + blue-chalk `#4C86C9`. Register note: heritage is an
aesthetic register only — no BSE/exchange affiliation is claimed
anywhere in copy.

## Shared truth constraints (all variants)

- Every figure traces to `docs/portfolios.md` or the NSE index CSVs;
  signal ranks from `data/final_portfolio/final_portfolio_24.csv`.
- 1/N wording: Core Momentum holds 24 names, OM25/TL25 hold 25 —
  pages say "24–25 stocks a portfolio" (fixed after review caught a
  1/24-vs-25 inconsistency).
- The regulatory footer line is a bracketed placeholder on every
  variant — founder to supply; never invent it.
- v2's interface card is labeled "design preview"; its data is real.

## Review trail

All three passed the impeccable mechanical detector (findings fixed
or justified: bone ground = pinned Ramp signature; stat-strip /
quote-board grammar; v3 body-size clustering carried by the Besley
display scale). Independent finish-review (degraded substitute agent,
fresh context): v1 ship; v2/v3 fix → fix batch applied → verdict
pass recorded in the task transcript.
