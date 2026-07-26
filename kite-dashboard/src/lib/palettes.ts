/**
 * Palette system metadata (DESIGN.md §2.6) — the client-side registry for
 * the six user-selectable palettes shipped in src/styles/marketworks/.
 *
 * next-themes stamps BOTH `class` and `data-palette` on <html>
 * (see providers.tsx): the palette sheets select on [data-palette="…"],
 * while `midnight` maps to the `dark` class so shadcn's dark variant and
 * the Midnight token block fire together. `mint` is the :root default.
 *
 * The chosen palette persists per-device via next-themes (localStorage)
 * and across devices via Clerk `unsafeMetadata.palette` (a user-writable
 * UI preference — never trusted server-side; validated here on read).
 */

export const PALETTES = [
  { name: "mint",     label: "Mint",     swatch: "#0C7A62", ring: "#55C374" },
  { name: "ocean",    label: "Ocean",    swatch: "#1263C7", ring: "#E8A33D" },
  { name: "amber",    label: "Amber",    swatch: "#A05A0A", ring: "#0B7E65" },
  { name: "coral",    label: "Coral",    swatch: "#E0604D", ring: "#17697E" },
  { name: "charcoal", label: "Charcoal", swatch: "#2B2B2B", ring: "#E8A33D" },
  { name: "midnight", label: "Midnight", swatch: "#0C1219", ring: "#58A6E8" },
] as const;

export type PaletteName = (typeof PALETTES)[number]["name"];

export const PALETTE_NAMES = PALETTES.map((p) => p.name) as readonly PaletteName[];

/** Theme values next-themes manages: the palettes plus its own system trio. */
export const THEME_VALUES = [...PALETTE_NAMES, "system", "light", "dark"];

/**
 * next-themes value map. MUST be complete: when a `value` prop is present,
 * next-themes removes the data attribute for any theme missing from the map
 * (v0.4.6 behavior — verified) — so every theme maps, identity for most.
 * `midnight` emits "dark" (fires the legacy dark class variant + the
 * Midnight token block; palettes.css selects `.dark` for it).
 */
export const THEME_VALUE_MAP = {
  mint: "mint",
  ocean: "ocean",
  amber: "amber",
  coral: "coral",
  charcoal: "charcoal",
  midnight: "dark",
  light: "light",
  dark: "dark",
  system: "system",
} as const;

export function isPaletteName(v: unknown): v is PaletteName {
  return typeof v === "string" && (PALETTE_NAMES as readonly string[]).includes(v);
}

/**
 * Resolve any theme value (palette name, "light"/"dark"/"system"-resolved)
 * to whether the surface is dark — for consumers that need a binary
 * (sonner, chart libs).
 */
export function isDarkTheme(theme: string | undefined, resolvedTheme: string | undefined): boolean {
  const v = theme === "system" || theme === undefined ? resolvedTheme : theme;
  return v === "midnight" || v === "dark";
}
