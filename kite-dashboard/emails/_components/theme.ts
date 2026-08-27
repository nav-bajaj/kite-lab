/**
 * Email design tokens — the v2 single-green system, translated for email.
 *
 * Why these differ from the web tokens (RESEARCH.md):
 *  - No web fonts. @font-face is ~24% supported and Gmail honours it on no
 *    platform, so Fraunces/Outfit cannot travel. Georgia carries the serif
 *    voice; a system sans carries UI text. The fallback IS the design.
 *  - No pure #000/#fff. Clients that auto-invert mangle absolutes; near
 *    tones survive.
 *  - Colour and STRUCTURE carry the brand here, because typography can't.
 *    That is why this file is mostly colour and spacing.
 */

export const color = {
  // ground
  page: "#eef2ef", // outside the card — slightly deeper than the site's mist
  card: "#ffffff",
  soft: "#f4f7f5",
  line: "#e3e8e5",
  lineStrong: "#c9d2cc",

  // ink
  ink: "#141a17",
  grey: "#5c6663",
  greySoft: "#79837f",

  // the green
  green: "#0b7e52",
  greenVivid: "#14a468",
  greenTint: "#dff4e8",
  greenDeep: "#0a3b28",
  greenOnDeep: "#bfebd8",

  // accent triads, straight from the guide — bg / line / fg
  acc1: { bg: "#dff4e8", line: "#14a468", fg: "#0a3b28" },
  acc2: { bg: "#fff1ce", line: "#f5b73e", fg: "#6b4a08" },
  acc3: { bg: "#e2eeff", line: "#2179e8", fg: "#123c77" },
  acc4: { bg: "#fde5de", line: "#e85d45", fg: "#6e2114" },
} as const;

export const font = {
  serif: "Georgia, 'Times New Roman', Times, serif",
  sans:
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
  mono: "'SF Mono', SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace",
} as const;

/** Outer width. 560–600px is the email safe zone; wider clips in Outlook's
 *  reading pane and on small phones. */
export const WIDTH = 600;

/** Substituted by Python at send time. Templates default their props to
 *  these literals so `email export` emits the placeholder (PLAN §3). */
export const TOKEN = {
  unsubscribe: "{{unsubscribe_url}}",
  preferences: "{{preferences_url}}",
} as const;
