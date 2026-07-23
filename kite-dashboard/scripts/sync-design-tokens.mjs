/**
 * Sync the design-system token stylesheets from the marketworks-design repo
 * into this app (Vercel can't reach the sibling repo at build time, so the
 * sheets are vendored and committed).
 *
 *   node scripts/sync-design-tokens.mjs
 *
 * Source of truth: ../marketworks-design (tokens/palettes.ts et al).
 * After changing tokens there: run its `npm run gen:palettes` + tests,
 * then run this script here and commit both files with the design-repo
 * commit hash it reports.
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { execSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const designRepo = resolve(here, "../../../marketworks-design");
const outDir = resolve(here, "../src/styles/marketworks");
mkdirSync(outDir, { recursive: true });

let rev = "unknown";
try {
  rev = execSync("git rev-parse --short HEAD", { cwd: designRepo }).toString().trim();
} catch {}

const stamp = (name) =>
  `/* VENDORED from marketworks-design@${rev} (${name}) — do not hand-edit.\n` +
  ` * Re-sync: node scripts/sync-design-tokens.mjs */\n`;

for (const [src, out] of [
  ["src/styles.css", "tokens.css"],
  ["src/palettes.css", "palettes.css"],
]) {
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- dev-time script; paths resolved from module-relative constants, no user input
  const css = readFileSync(resolve(designRepo, src), "utf8");
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- same: constant-derived output path under src/styles/marketworks
  writeFileSync(resolve(outDir, out), stamp(src) + css);
  console.log(`synced ${src} -> src/styles/marketworks/${out}`);
}
console.log(`design repo @ ${rev}`);
