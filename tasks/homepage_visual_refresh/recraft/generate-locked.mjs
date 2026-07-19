// Locked-palette grain illustrations: cool base + purple + a new warm marigold.
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

// Locked palette: mist, lichen, signal, ink, marigold (warm), purple (cool spot).
const COLORS = [
  { rgb: [236, 243, 239], weight: 0.2 }, // mist
  { rgb: [20, 113, 95], weight: 0.22 }, // lichen
  { rgb: [85, 195, 116], weight: 0.16 }, // signal
  { rgb: [26, 26, 26], weight: 0.12 }, // ink
  { rgb: [232, 163, 61], weight: 0.18 }, // marigold (warm)
  { rgb: [151, 80, 248], weight: 0.12 }, // purple (cool spot)
];

const STYLE =
  "soft grainy stippled risograph texture across the whole image, fine speckled grain, painterly and " +
  "atmospheric, flat simple forms with grainy shading, generous negative space, contemplative conceptual " +
  "editorial op-ed illustration, New York Times illustration mood, metaphorical not literal, no text, no " +
  "words, no charts, no numbers, no logos. Colour palette limited to mist off-white, deep teal green, " +
  "bright signal green, soft ink black, a warm welcoming marigold-gold, and a muted purple accent; warm " +
  "marigold light, green hills, ink figures, purple as a quiet shadow accent; no other colours";

const JOBS = {
  hero: "a lone calm figure standing on a gentle hill at dawn, watching a wide horizon of soft layered mountain ranges that rise and fall like distant peaks; unhurried, patient, quietly confident",
  research: "a large old magnifying glass resting over a landscape of soft layered hills, gently revealing a faint winding path; careful study of the past",
};

const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(JOBS);
const outDir = path.join(HERE, "raster");
await fs.mkdir(outDir, { recursive: true });

for (const name of names) {
  const subject = JOBS[name];
  if (!subject) { console.error(`unknown job: ${name}`); continue; }
  const body = {
    prompt: `${subject}. ${STYLE}.`,
    model: "recraftv3",
    style: "digital_illustration",
    substyle: "grain",
    size: "1024x1024",
    n: 1,
    response_format: "url",
    controls: { colors: COLORS },
  };
  const res = await fetch("https://external.api.recraft.ai/v1/images/generations", {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) { console.error(`[${name}] HTTP ${res.status}`, JSON.stringify(json).slice(0, 400)); continue; }
  const url = json?.data?.[0]?.url;
  if (!url) { console.error(`[${name}] no url`, JSON.stringify(json).slice(0, 300)); continue; }
  const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
  await fs.writeFile(path.join(outDir, `locked_${name}.png`), buf);
  console.log(`[locked_${name}] saved (${buf.length} bytes)`);
}
