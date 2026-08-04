// Watercolor test — Recraft V4.1 Pro (prompt-only), bright on-brand palette,
// finance/research/optimistic subjects. node generate-watercolor.mjs [name ...]
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const env = await fs.readFile("/Users/navdeep/kite-lab/.env", "utf8");
const KEY = env
  .split("\n")
  .find((l) => l.trim().startsWith("RECRAFT_API_KEY"))
  ?.split("=").slice(1).join("=").trim().replace(/^["']|["']$/g, "");
if (!KEY) { console.error("no key"); process.exit(1); }

// Bright, light, cheerful, on-brand — fresh greens + soft warm morning light.
const COLORS = [
  { rgb: [236, 243, 239], weight: 0.2 }, // mist
  { rgb: [85, 195, 116], weight: 0.22 }, // fresh signal green
  { rgb: [20, 113, 95], weight: 0.12 }, // lichen
  { rgb: [180, 168, 214], weight: 0.14 }, // soft periwinkle
  { rgb: [206, 224, 236], weight: 0.14 }, // pale sky
  { rgb: [245, 232, 205], weight: 0.18 }, // soft warm sunlight
];

const STYLE =
  "A soft loose watercolor painting with gentle translucent washes and visible cold-press paper texture, " +
  "delicate airy brushwork, light and luminous. Bright, fresh, hopeful and optimistic, calm, generous " +
  "negative space, plenty of soft light. No text, no words, no logos.";

const JOBS = {
  hero: "a calm person standing in bright soft morning light, gently tending a small cluster of green plants growing upward from the earth; unhurried, quietly hopeful, a feeling of steady growth",
  research: "a bright sunlit wooden desk beside a window, with an open notebook of faint handwriting, a magnifying glass and a small potted plant catching the warm morning light; patient, hopeful study",
  rank: "several slender young trees of clearly different heights growing on a gentle sunlit hill, all reaching upward toward a bright soft sun, the tallest catching the most light; rising growth and strength",
};

const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(JOBS);
const outDir = path.join(HERE, "watercolor");
await fs.mkdir(outDir, { recursive: true });

for (const name of names) {
  const subject = JOBS[name];
  if (!subject) { console.error(`unknown job: ${name}`); continue; }
  const res = await fetch("https://external.api.recraft.ai/v1/images/generations", {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: `${subject}. ${STYLE}`,
      model: "recraftv4_1_pro",
      size: "2048x2048",
      n: 1,
      response_format: "url",
      controls: { colors: COLORS },
    }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) { console.error(`[${name}] HTTP ${res.status}`, JSON.stringify(json).slice(0, 300)); continue; }
  const url = json?.data?.[0]?.url;
  if (!url) { console.error(`[${name}] no url`, JSON.stringify(json).slice(0, 200)); continue; }
  const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
  await fs.writeFile(path.join(outDir, `${name}.png`), buf);
  console.log(`[${name}] saved (${buf.length} bytes)`);
}
