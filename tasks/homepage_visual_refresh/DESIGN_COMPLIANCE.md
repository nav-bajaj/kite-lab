# DESIGN_COMPLIANCE — per-unit brand review checklist

Fill this for every token set / primitive / section before sign-off. Source of
truth: `~/marketworks-design/DESIGN.md`. A ❌ blocks the unit. This is the gate that
would have caught the mock's font-delivery drift.

## Typography
- [ ] Headings/titles: **Fraunces** only (weights 400/500/600 — **never bold/700**).
- [ ] Body/UI/labels: **Outfit** only. Data/tickers: system mono.
- [ ] No other font family anywhere. No serif-in-paragraph mixing.
- [ ] Fonts loaded via **self-hosted `next/font`** — **no** Google Fonts CDN `<link>`,
      no `@import url()`. (CDN is CSP-blocked in prod and is how the mock drifted.)
- [ ] Type scale + tracking per DESIGN.md §3; `text-wrap: balance` on h1–h3.

## Color
- [ ] Only role tokens / brand tokens — **no raw hex in component code**.
- [ ] No off-palette colors. `signal-green` never used where semantic `positive`
      belongs (identity ≠ meaning). `purple` sparing (≤1 moment/section).
- [ ] Light-locked: no `dark:` variants / no theme toggle on marketing.
- [ ] Body text ≥ 4.5:1 on its background (muted greys checked, not assumed).

## Surface & layout
- [ ] Base is near-white `#FAFCFB` (tinted), **not** pure `#FFFFFF`.
- [ ] Colored sections are **inset rounded panels** (side margins + `radius-card` +
      shadow), **never** full-bleed edge-to-edge bands. White flows continuously.
- [ ] `mist` still load-bearing (primary panel/card tint).
- [ ] Section padding ≥ 64px mobile / ≥ 96px desktop (DESIGN.md §4).
- [ ] No nested cards. No "icon-tile + 1-line heading + 2-line body" SaaS card grid.

## Elevation & radius
- [ ] Cards/panels use the ink-tinted shadow scale (`--mw-shadow*`) — **no black
      shadows, no hard directional drop**.
- [ ] Controls/buttons `radius 8px`; cards/panels `radius-card 24px` (hero 32px);
      nav/CTA pills `9999px`.

## Motion
- [ ] Easing = expo-out `cubic-bezier(.22,1,.36,1)` / decelerate only. **No bounce/
      overshoot** (except a single tiny stat pop, if any).
- [ ] Durations per scale (0.15 UI / 0.2 reveal / ~0.6 big-resolve). Motion is rare.
- [ ] Reveals **enhance an already-visible default** (no visibility gated on JS).
- [ ] `prefers-reduced-motion`: parallax/drift/draw off, content renders complete.
- [ ] Ambient background contained (not full-page), `content-visibility:auto`,
      pauses on hidden tab. **No animated hero metric counters** (DESIGN.md §9).

## Graphics & halftone
- [ ] Illustrations: line-based editorial (Recraft), **self-hosted static SVG**;
      no flat-vector SaaS, no faces, one signal-green focal accent max.
- [ ] Halftone: baked monochrome (ink-on-mist or lichen-on-white), on-register.
- [ ] No external asset host, no WASM/Rive/Lottie (CSP + register-row rule).

## Copy & compliance
- [ ] Brand copy verbatim; no invented claims/data (flag placeholders explicitly).
- [ ] Buttons = verb + object. No em dashes in NEW microcopy.
- [ ] Compliance strings present where required: "SEBI Registered Research Analyst"
      + market-risk disclaimer. Sample data labeled as sample.

## Accessibility & responsive
- [ ] Keyboard-reachable; visible focus = lichen ring.
- [ ] Renders 360 / 768 / 1080; grids collapse < 860. No horizontal overflow.
- [ ] Illustration `aria-hidden`; meaning lives in adjacent text.

## Sign-off
- [ ] Layer-1 deterministic gate green (contract test, lint, Playwright, Lighthouse).
- [ ] Impeccable `critique`/`audit` run; findings resolved.
- [ ] Founder visual sign-off on screenshots (normal + reduced-motion + 3 widths).
