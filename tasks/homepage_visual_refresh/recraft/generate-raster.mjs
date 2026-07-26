// Recraft raster (grain / editorial) generator — homepage_visual_refresh Phase C.
// Targets the grainy atmospheric editorial register (NYT-illustrator reference),
// adapted to the brand palette. Raster PNG kept as-is (grain must survive).
// Usage: node generate-raster.mjs [name ...]

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
  console.error("no key");
  process.exit(1);
}

// Bias toward the brand palette + a cool atmospheric secondary.
const COLORS = [
  { rgb: [236, 243, 239], weight: 0.25 }, // mist ground/sky
  { rgb: [20, 113, 95], weight: 0.3 }, // lichen
  { rgb: [85, 195, 116], weight: 0.2 }, // signal-green
  { rgb: [26, 26, 26], weight: 0.15 }, // ink
  { rgb: [66, 96, 142], weight: 0.1 }, // denim (atmosphere)
];

// Style descriptor distilled from the reference (grain + atmosphere + metaphor).
const STYLE =
  "soft grainy stippled risograph texture across the whole image, fine speckled grain, " +
  "painterly and atmospheric, flat simple forms with grainy shading, muted limited palette of " +
  "deep teal green, sage green, mist off-white and soft ink, a vast quiet sky, generous negative space, " +
  "contemplative conceptual editorial op-ed illustration, New York Times illustration mood, " +
  "metaphorical not literal, no text, no words, no charts, no logos, no numbers";

const JOBS = {
  hero: "a lone calm figure standing on a gentle hill at dawn, watching a wide horizon of soft layered mountain ranges that rise and fall like distant peaks; unhurried, patient, quietly confident",
  research: "a large old magnifying glass resting over a landscape of layered translucent hills, gently revealing a faint path winding through them; careful study of the past",
};

const names = process.argv.slice(2).length
  ? process.argv.slice(2)
  : Object.keys(JOBS);
const outDir = path.join(HERE, "raster");
await fs.mkdir(outDir, { recursive: true });

for (const name of names) {
  const subject = JOBS[name];
  if (!subject) {
    console.error(`unknown job: ${name}`);
    continue;
  }
  const body = {
    prompt: `${subject}. ${STYLE}`,
    model: "recraftv3",
    style: "digital_illustration",
    substyle: "grain",
    size: "1024x1024",
    n: 1,
    response_format: "url",
    controls: { colors: COLORS },
  };
  const res = await fetch(
    "https://external.api.recraft.ai/v1/images/generations",
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
    console.error(`[${name}] HTTP ${res.status}`, JSON.stringify(json).slice(0, 500));
    continue;
  }
  const url = json?.data?.[0]?.url;
  if (!url) {
    console.error(`[${name}] no url`, JSON.stringify(json).slice(0, 300));
    continue;
  }
  const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
  const out = path.join(outDir, `${name}.png`);
  await fs.writeFile(out, buf);
  console.log(`[${name}] saved ${out} (${buf.length} bytes)`);
}
