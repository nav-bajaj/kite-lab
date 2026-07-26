// Recraft V4.1 vector illustration generator (homepage_visual_refresh, Phase C).
// Reads RECRAFT_API_KEY from repo-root .env. Generates native SVG, downloads to
// ./raw/. Deterministic palette/stroke normalization is a separate step.
// Usage: node generate.mjs [name ...]   (no args = generate all)

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

const env = await fs.readFile("/Users/navdeep/kite-lab/.env", "utf8");
const KEY = env
  .split("\n")
  .find((l) => l.trim().startsWith("RECRAFT_API_KEY"))
  ?.split("=")
  .slice(1)
  .join("=")
  .trim()
  .replace(/^["']|["']$/g, "");
if (!KEY) {
  console.error("RECRAFT_API_KEY not found in /Users/navdeep/kite-lab/.env");
  process.exit(1);
}

// Bias generation toward the brand palette (normalization enforces exact hexes).
const COLORS = [
  { rgb: [20, 113, 95], weight: 0.4 }, // lichen
  { rgb: [26, 26, 26], weight: 0.3 }, // ink
  { rgb: [85, 195, 116], weight: 0.2 }, // signal-green
  { rgb: [236, 243, 239], weight: 0.1 }, // mist ground
];

const STYLE =
  "editorial single-weight line illustration, uniform thin stroke, round line caps, " +
  "flat, only 3 or 4 colours, deep teal and one bright green accent on a near-white ground, " +
  "generous negative space, no shading, no gradient, no text, no words, " +
  "New Yorker / Financial Times line-drawing register, minimal and calm";

const JOBS = {
  hero: "a scatter of small dots resolving into one calm ascending line, a single circled point marking the leading edge; abstract stock momentum",
  rank: "a neat vertical stack of horizontal bars of decreasing length, the top bar highlighted; ranking the market",
  build: "a small grid of nodes gathering into one tidy stacked list of cards; assembling a portfolio",
  follow: "a single clean line tracing a marked path with a highlighted current point, like following a route",
  research: "a smooth bell curve over a baseline with a few sample dots and one highlighted point; statistics and validation",
  portfolios: "three parallel lines of different rhythm sharing one origin point, fanning gently upward; three strategies",
};

const want = process.argv.slice(2);
const names = want.length ? want : Object.keys(JOBS);
const outDir = path.join(HERE, "raw");
await fs.mkdir(outDir, { recursive: true });

for (const name of names) {
  const subject = JOBS[name];
  if (!subject) {
    console.error(`unknown job: ${name}`);
    continue;
  }
  const body = {
    prompt: `${subject}. ${STYLE}`,
    model: "recraftv4_1_vector",
    size: "1024x1024",
    n: 1,
    response_format: "url",
    controls: { colors: COLORS },
  };
  const res = await fetch(
    "https://external.api.recraft.ai/v1/images/generations/vector",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    },
  );
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    console.error(`[${name}] HTTP ${res.status}`, JSON.stringify(json).slice(0, 400));
    continue;
  }
  const url = json?.data?.[0]?.url;
  if (!url) {
    console.error(`[${name}] no url in response`, JSON.stringify(json).slice(0, 400));
    continue;
  }
  const svg = await (await fetch(url)).text();
  const out = path.join(outDir, `${name}.svg`);
  await fs.writeFile(out, svg);
  console.log(`[${name}] saved ${out} (${svg.length} bytes)`);
}
