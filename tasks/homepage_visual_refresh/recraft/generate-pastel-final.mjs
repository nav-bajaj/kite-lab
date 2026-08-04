// Final pastel set for the homepage — cool + bright + on-brand (no warm grounds).
// Recraft V3 digital_illustration / pastel_gradient. n=2 for curation.
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

// COOL + bright, on-brand. No warm (the rust/red grounds came from warm hints).
const COLORS = [
  { rgb: [236, 243, 239], weight: 0.22 }, // mist
  { rgb: [85, 195, 116], weight: 0.24 }, // fresh signal green
  { rgb: [20, 113, 95], weight: 0.14 }, // lichen
  { rgb: [180, 168, 214], weight: 0.14 }, // soft lavender
  { rgb: [206, 224, 236], weight: 0.14 }, // pale sky
  { rgb: [200, 230, 214], weight: 0.12 }, // pale mint
];

const STYLE =
  "Soft bright pastel illustration with smooth clean light gradients, airy and fresh, modern and calm. " +
  "COOL palette only: fresh greens, mist off-white, soft lavender, pale sky blue; NO warm colours, no rust, " +
  "no orange, no red, no brown grounds. Bright, light, cheerful and hopeful, generous space. No text, no logos.";

const JOBS = {
  hero: "a calm person tending a cluster of small green plants growing upward from a gentle green hill in bright soft morning light; unhurried, quietly hopeful, steady growth",
  rank: "several slender young trees of clearly different heights on a gentle green hill under a bright soft sky, all reaching upward, the tallest catching the most light; rising strength",
  build: "a gentle hand carefully placing a few of the ripest round fruits into a small basket held below, a leafy branch above; choosing only the best few",
  follow: "a small figure walking along a bright winding path curving forward over gentle green hills toward a soft bright horizon; a clear hopeful route to follow",
  research: "a bright airy desk beside a window with an open notebook, a magnifying glass and a small potted plant, soft morning light; patient hopeful study",
  portfolios: "three healthy potted plants of clearly different character standing side by side on a windowsill in bright soft light; three distinct temperaments",
};

const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(JOBS);
const outDir = path.join(HERE, "set_pastel2");
await fs.mkdir(outDir, { recursive: true });

for (const name of names) {
  const subject = JOBS[name];
  if (!subject) { console.error(`unknown job: ${name}`); continue; }
  const res = await fetch("https://external.api.recraft.ai/v1/images/generations", {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: `${subject}. ${STYLE}`,
      model: "recraftv3",
      style: "digital_illustration",
      substyle: "pastel_gradient",
      size: "1024x1024",
      n: 2,
      response_format: "url",
      controls: { colors: COLORS },
    }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) { console.error(`[${name}] HTTP ${res.status}`, JSON.stringify(json).slice(0, 200)); continue; }
  const data = json?.data ?? [];
  for (let i = 0; i < data.length; i++) {
    if (!data[i]?.url) continue;
    const buf = Buffer.from(await (await fetch(data[i].url)).arrayBuffer());
    await fs.writeFile(path.join(outDir, `${name}_${i + 1}.png`), buf);
    console.log(`[${name}_${i + 1}] saved (${buf.length} bytes)`);
  }
}
