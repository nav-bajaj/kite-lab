# clay.com decoded — typography + color system (2026-08-06)

Live-DOM study (Playwright, 1440px viewport) of clay.com's homepage:
computed styles harvested element-by-element, plus their entire token
sheet, which Webflow ships un-minified as CSS custom properties.
Screenshots: `references/clay_home_hero.png`,
`clay_home_yellow_card.png`, `clay_home_stacked_cards.png`.

## 1. Typography

### The faces

| Face | Role | Notes |
|---|---|---|
| **Roobert VF** (variable, 300–900) | EVERYTHING — display, body, UI, buttons | One family; hierarchy comes from size/weight/tracking, never from a second face |
| **Space Mono** 400/700 | tiny meta labels, code-ish accents | loaded but sparing |
| **Canela** (serif) | declared, unused on the homepage | reserved for editorial pages |
| Phosphor | icon font | — |

The core lesson: **one variable sans + optical tightening**. No
display/body font pairing on the homepage at all. Contrast is made
with weight (400 vs 500 vs 575 vs 600), scale jumps, and color —
not typeface changes.

### The scale (computed, desktop)

| Slot | Size/line | Weight | Tracking | Notes |
|---|---|---|---|---|
| h1 hero | 88/88 (**1.0**) | **575** (vf) | **−4%** (−3.52px) | white on dark field |
| h2 section | 72/72 (1.0) | 500 | −3% | black on white |
| h3 feature | 48/48 (1.0) | 500 | −4% | two-tone (see below) |
| h2 CTA | 44/48.4 (1.1) | 500 | −2% | |
| lede | 24/31.2 (1.3) | 400 | 0 | |
| body | 20/25 (1.25) | 400 | 0 | generous for marketing body |
| body-s | 16/22.4 (1.4) | 400 | 0 | cards, footer |
| button | 16–18 | 500 | **−1%** | buttons are tracked tight too |
| eyebrow | 12/14.4 | 600 | **+9%** (1.08px) | UPPERCASE, the pill labels |
| micro-label | 10/12 | 600 | +8% | UPPERCASE, muted color |

Rules extracted:
- Display line-height is **exactly 1.0** at ≥48px; 1.1 at 44px; body
  never below 1.25.
- Tracking scales with size: −2% at 44px → −4% at 88px. Buttons −1%.
- Weight stays in the 400–600 band; the hero's 575 is a variable-font
  micro-step (not bold — "medium-plus").
- Eyebrows/labels: small + SEMIBOLD + UPPERCASE + wide tracking
  (+8–9%) — the exact inverse of the display treatment. This
  small-loose vs huge-tight opposition is most of their typographic
  personality.

### Mapping to Marketworks

We keep **Stack Sans Text** (headings) + **Outfit** (body) + mono
labels — a font swap is not the lesson. Adopted instead:
- hero tracking −0.025em → **−0.035em**, leading 1.02 → **1.0**;
- mono index captions stay (they already play the eyebrow role) but
  gain per-section accent color (see §3);
- keep weights ≤600 on display sizes.

## 2. Color

### Their token system (verbatim, from their own CSS vars)

Two neutral ramps + eight named accent families, each 50→950:

- **oat** (warm neutral — THE ground): 50 `#fffcfa` · 100 `#f9f8f6` ·
  200 `#f3f2ed` · 300 `#eee9df` · 400 `#dad4c8` · 500 `#c0bbaf` ·
  600 `#9f9b93` · 700 `#85817a` · 800 `#55534e` · 900 `#363430` ·
  950 `#1b1a18`
- **grey** (cool neutral, product UI only): 50 `#f7f8f9` … 950 `#16181f`
- **blueberry** (blue): 100 `#d7ebfe` · 500 `#0382f7` · 900 `#002f67`
- **matcha** (green): 100 `#dbffe0` · 500 `#0dac65` · 900 `#03331d`
- **lemon** (yellow): 100 `#fff8d2` · 500 `#fbbd41` · 700 `#d08a11`
- **tangarine** (orange): 100 `#ffe9d5` · 500 `#fc8936` · 600 `#fa6900`
- **pomegranate** (red): 100 `#ffebec` · 500 `#e94d68`
- **ube** (violet): 100 `#e9e4ff` · 500 `#8b5cf6`
- **dragonfruit** (pink): 100 `#ffe5f7` · 500 `#ff7ad5`
- **slushie** (cyan): 100 `#e0f8ff` · 500 `#3bd3fd`

Marketing one-offs outside the ramps: vivid heading blue `#395AFA`,
highlighter-yellow CTA `#EEF773` / `#CBD810`, hero field deep green
`#035D44`.

### How the page deploys it

- Page ground: **white → warm near-whites** (`#FFFFFF`, `#FEFDFB`,
  `#F4F3F0`, footer `#FFFDF9`). The warm (oat) tint is deliberate:
  warm paper makes the cool vivids (blue, cyan) pop harder.
- Ink: black / oat-950 `#1b1a18`; secondary text oat-800 `#55534e`,
  muted labels oat-ish `#79756d`.
- Buttons: black pill + white pill (neutral pair), one
  highlighter-yellow CTA per screen. Vivid hue buttons only inside
  colored sections.
- The hero is the only full-saturation dark field; everything below
  is near-white with color carried by ELEMENTS (cards, pills,
  buttons, headings) — exactly the direction the founder named for
  our below-hero region.

### The signature move: the per-section monochrome triad

Measured off the four stacked feature cards (`.home-feature_item`):

| Card | pastel card bg | vivid (pill + CTA) | deep heading ink |
|---|---|---|---|
| Data | `#F0F8FF` | `#395AFA` | `#001433` |
| Agents | `#FFF3ED` | `#B53D0A` | `#381005` |
| Orchestration | `#FCFEE2` | `#808000` | `#102B03` |
| Execution | `#FFF0FA` | `#CC089E` | `#46022F` |

One hue per section, three tones: **tint (surface) · vivid
(action/pill) · deep (text)**. Headings are TWO-TONE within the same
hue — first phrase in the deep ink, second phrase in the vivid (or a
mid shade). Buttons inside the section take the vivid with white
text. This triad maps 1:1 onto our existing `accN-bg / accN-line /
accN-fg` token trio — our system already has the sockets; the study
retunes the values to Clay vibrance and starts USING the trio as a
per-section system.

Also noted: 48px top radius on the stacked cards (huge, friendly),
pill labels echoed as a stack of offset pastel pills behind the
active one, and section media always sitting on the section's tint.

## 3. What this study changes on our branch (design_studies_clay)

1. **Two themes replace the six-palette picker** (marketing scope
   first): Light = Ocean-based Clay formula; Dark = ink-navy
   companion. Marketing nav gets a sun/moon toggle; the dashboard
   picker's fate is a merge-checklist item.
2. **Light theme**: warm near-white paper ground (`#FBFAF7`), white
   cards, warm hairlines, ink `#1B1A17`; primary stays Horizon blue
   `#0A5CFF`; six accent triads retuned to Clay vibrance
   (blue/sun/matcha/coral/ube/magenta — values in globals.css).
3. **Dark theme**: deep ink-navy ground (`#0A111F`), brightened
   vivids (primary `#4D8DFF`), triads inverted (deep wash · bright
   line · pale text), hero sky variant that exits into the dark
   ground.
4. **Typography tightening** per §1 (tracking/leading on display,
   colored eyebrows).
5. Vibrant color arrives through ELEMENTS on the near-white ground:
   accent-framed cards, vivid pills, colored section eyebrows,
   two-tone headings — never through tinted page bands.
