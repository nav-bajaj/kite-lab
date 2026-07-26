// A/B accent test: same hero subject, purple vs warm accent, tightened cool base.
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

const SUBJECT =
  "a lone calm figure standing on a gentle hill at dawn, watching a wide horizon of soft " +
  "layered mountain ranges that rise and fall like distant peaks; unhurried, patient, quietly confident";
const STYLE =
  "soft grainy stippled risograph texture across the whole image, fine speckled grain, painterly and " +
  "atmospheric, flat simple forms with grainy shading, generous negative space and a vast quiet sky, " +
  "contemplative conceptual editorial op-ed illustration, New York Times illustration mood, metaphorical " +
  "not literal, no text, no words, no charts, no numbers, no logos. " +
  "Muted cool base of deep teal green, sage green, mist off-white, soft ink black and dusky blue";

const BASE_COLORS = [
  { rgb: [236, 243, 239], weight: 0.24 }, // mist
  { rgb: [20, 113, 95], weight: 0.26 }, // lichen
  { rgb: [85, 195, 116], weight: 0.18 }, // signal
  { rgb: [26, 26, 26], weight: 0.12 }, // ink
  { rgb: [66, 96, 142], weight: 0.1 }, // denim
];

const VARIANTS = {
  hero_purple: { phrase: "a single muted purple accent", rgb: [151, 80, 248] },
  hero_warm: { phrase: "a single warm marigold-gold accent", rgb: [232, 155, 46] },
};

const outDir = path.join(HERE, "raster");
await fs.mkdir(outDir, { recursive: true });

for (const [name, v] of Object.entries(VARIANTS)) {
  const body = {
    prompt: `${SUBJECT}, with ${v.phrase} as the only bright note and no other saturated colours. ${STYLE}.`,
    model: "recraftv3",
    style: "digital_illustration",
    substyle: "grain",
    size: "1024x1024",
    n: 1,
    response_format: "url",
    controls: { colors: [...BASE_COLORS, { rgb: v.rgb, weight: 0.1 }] },
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
  await fs.writeFile(path.join(outDir, `${name}.png`), buf);
  console.log(`[${name}] saved (${buf.length} bytes)`);
}
