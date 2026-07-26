// Final grain illustration set (homepage_visual_refresh, Phase C).
// Locked palette: mist / lichen / signal / ink + purple + marigold. n=2 per
// subject for curation. Usage: node generate-final.mjs [name ...]
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

const COLORS = [
  { rgb: [236, 243, 239], weight: 0.2 }, // mist
  { rgb: [20, 113, 95], weight: 0.22 }, // lichen
  { rgb: [85, 195, 116], weight: 0.16 }, // signal
  { rgb: [26, 26, 26], weight: 0.12 }, // ink
  { rgb: [232, 163, 61], weight: 0.18 }, // marigold
  { rgb: [151, 80, 248], weight: 0.12 }, // purple
];

const STYLE =
  "soft grainy stippled risograph texture across the whole image, fine speckled grain, painterly and " +
  "atmospheric, flat simple forms with grainy shading, generous negative space, contemplative conceptual " +
  "editorial op-ed illustration, New York Times illustration mood, metaphorical not literal, no text, no " +
  "words, no charts, no numbers, no logos. Colour palette strictly limited to mist off-white, deep teal " +
  "green, bright signal green, soft ink black, a warm welcoming marigold-gold, and a muted purple accent; " +
  "warm marigold light, green hills, ink figures, purple as a quiet accent; NO blue, NO cyan, no other colours";

const JOBS = {
  hero: "a lone calm figure standing on a grassy hill at dawn, watching a wide horizon of soft layered mountain ranges that rise and fall like distant peaks; unhurried, patient, quietly confident",
  rank: "a range of soft rounded hills of clearly stepped increasing heights, a small flag planted on the single tallest peak; spotting the leaders of the landscape",
  build: "calm hands carefully stacking a few smooth flat stones into a small balanced cairn on a grassy hill; assembling something steady and deliberate",
  follow: "a small lone figure walking along a clear winding footpath over gentle rolling hills toward a distant marked point; calmly following a route",
  research: "a large old magnifying glass resting over a landscape of soft layered hills, gently revealing a faint winding path through them; careful study of the past",
  portfolios: "three distinct winding footpaths of different character diverging from a single hilltop across gentle rolling hills; three ways forward",
};

const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(JOBS);
const outDir = path.join(HERE, "final");
await fs.mkdir(outDir, { recursive: true });

for (const name of names) {
  const subject = JOBS[name];
  if (!subject) { console.error(`unknown job: ${name}`); continue; }
  const res = await fetch("https://external.api.recraft.ai/v1/images/generations", {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: `${subject}. ${STYLE}.`,
      model: "recraftv3",
      style: "digital_illustration",
      substyle: "grain",
      size: "1024x1024",
      n: 2,
      response_format: "url",
      controls: { colors: COLORS },
    }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) { console.error(`[${name}] HTTP ${res.status}`, JSON.stringify(json).slice(0, 400)); continue; }
  const data = json?.data ?? [];
  for (let i = 0; i < data.length; i++) {
    if (!data[i]?.url) continue;
    const buf = Buffer.from(await (await fetch(data[i].url)).arrayBuffer());
    await fs.writeFile(path.join(outDir, `${name}_${i + 1}.png`), buf);
    console.log(`[${name}_${i + 1}] saved (${buf.length} bytes)`);
  }
}
