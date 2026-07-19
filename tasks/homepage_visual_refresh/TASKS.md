# TASKS — implementation & review system

Branch: `beta_gtm_mvp_redesign` (off `beta_gtm_mvp`). Owners: 🤖 Claude Code (lead),
👤 founder (sign-off / Recraft / Mobbin). Codex optional for isolated components.

## Governing principles (why this order avoids rework)

1. **Foundation before composition.** Tokens → primitives → sections → pages. A
   section can only use tokens and primitives that already passed review, so it
   physically can't drift (the font/color drift in the HTML mocks came from
   freehand building *ahead* of the system — we invert that).
2. **Build on `@marketworks/design`, never freehand.** No raw hex, no CDN fonts,
   no ad-hoc CSS. Components consume role tokens + self-hosted `next/font`.
3. **One unit at a time, gated.** Each token set / primitive / section passes the
   two-layer review (below) AND a founder visual sign-off before the next starts.
   Small, reversible units; no big-bang.
4. **Visual verification is mandatory, not optional.** Every unit is screenshotted
   (Playwright) in normal + reduced-motion + at 3 widths before sign-off — closing
   the "built blind" hole that the mock phase had.

## The two-layer review gate (applied to EVERY unit)

**Layer 1 — deterministic (must be green):**
- Token-contract test (design pkg) passes; `.mw-brand` mirror matches.
- Banned-pattern scan clean: no raw hex in components, no `font-family` other than
  the brand vars, no external font/asset URL, no `dark:` on marketing surfaces, no
  full-bleed colored band (colored sections must be inset panels).
- Playwright: reduced-motion renders complete; page light-locked under emulated
  system-dark; **zero CSP violations / zero blocked external requests**; renders at
  360 / 768 / 1080; grids collapse < 860.
- Lighthouse mobile ≥ 90; background loop pauses on hidden tab.

**Layer 2 — judgment:**
- `DESIGN_COMPLIANCE.md` checklist filled for the unit (fonts, palette, surface,
  radius, elevation, motion, halftone, graphics, a11y, copy).
- Impeccable `critique` (UX) and/or `audit` (a11y/perf) run on the unit.
- `security-reviewer` subagent on ANY change to `next.config.ts` / CSP / headers.
- Founder visual sign-off on the screenshots.

Nothing advances to the next unit until both layers pass.

## Phase A — Foundation (tokens) 🤖 → 👤 sign-off  ⚠️ brand-contract
- [x] A1. Amended `~/marketworks-design/DESIGN.md`: new §2.5 (layered surface,
      inset-panel rule, ink-tinted shadow scale, tint ladder, radii), §6 `ease-expo`
      row, §9 "pure white" clarified, changelog `2026.07.19`. Mist kept as anchor.
- [x] A2. Tokens added to `@marketworks/design`: `surface` (base #FAFCFB, panel
      mist/tint/deep) + `shadow` (colors.ts), `radius.card/panel` (spacing.ts),
      `easing.expo` (motion.ts), exported (index.ts), shipped (src/styles.css).
      Mirrored into `kite-dashboard/globals.css` `.mw-brand` + `@theme` (bg-surface-*,
      rounded-card/panel, shadow-card/-hover/-panel/-soft, ease-expo).
- [x] A3. Token-contract test extended (22/22 green: base ≠ pure white, ink-tinted
      shadows, radii, expo, styles.css sync). Banned-pattern lint → deferred to a
      Phase-B pre-build step.
- **Gate:** ✅ contract tests green. ⏳ awaiting founder sign-off on the DESIGN.md
      amendment (nothing committed yet).

## Phase B — Shared primitives (build once, reuse) 🤖
Each is its own gated unit with a Playwright snapshot:
- [ ] B1. `SectionPanel` — inset rounded colored panel (variants base/mist/tint/
      lichen/deep); encodes the "inset, not edge-to-edge" rule.
- [ ] B2. `MarketingCard` — Corgi ink-tinted shadow, `radius-card`, tinted inner
      panel, hover lift, `↗` link. Replaces the flat-border card.
- [ ] B3. `Halftone` — baked-illustration wrapper + CSS dot-screen accent variant.
- [ ] B4. `FlowBackground` — contained ambient (rAF or Motion), `content-visibility`,
      reduced-motion static, hidden-tab pause.
- [ ] B5. Motion primitives — `Reveal` (expo-out, visible-by-default, reduced-motion
      safe) + SVG draw util. Adopt `motion` (`motion/react`, `LazyMotion`+`m`).
- [ ] B6. `MarketingNav` → floating glass pill (Acctual), lowercase wordmark, lichen
      CTA; scroll-shrink.
- [ ] B7. `Illustration` slot — placeholder → self-hosted Recraft SVG.

## Phase C — Illustrations (parallel; needs 👤 Mobbin refs) 🤖
- [ ] C1. Recraft Style-Lock from Mobbin refs + editorial line refs (RECRAFT_API_KEY).
- [ ] C2. Generate the 6 (see scratchpad `illustration_brief.md`) as native SVG.
- [ ] C3. Normalize (snap to hexes, force stroke, SVGO) → `svgr` components.
- [ ] C4. Bake halftone variants; self-host under `public/`. Verify zero CSP impact.

## Phase D — Homepage, section by section 🤖 → 👤 sign-off each
Rebuild `page.tsx` composing ONLY primitives. Per section: build → checklist →
impeccable critique → Playwright (motion/reduced-motion/light-lock/CSP/responsive)
→ founder sign-off → next. Order: D1 Nav · D2 Hero · D3 Welcome · D4 How-it-works ·
D5 Research · D6 Portfolios · D7 CTA · D8 Footer.

## Phase E — Propagate to other pages 🤖 (only after D locked)
- [ ] `/portfolios`, `/library`, `/sign-up`, `/insights` chrome adopt the same
      primitives. No re-layout beyond what the primitives give for free.

## Phase F — QA + ship 🤖 → 👤
- [ ] Full-page Playwright gate (all Layer-1 checks), Lighthouse, `security-reviewer`
      on any CSP/config touch.
- [ ] Deploy `beta_gtm_mvp_redesign` preview → verify live URL (Vercel MCP is 403;
      poll the URL). Merge to `beta_gtm_mvp` only when a coherent chunk is signed off.

## Still needed from founder
- Mobbin references (→ Phase C). · Sign-off on A1 DESIGN.md amendment. · Per-section
  sign-off in Phase D.
