// Style exploration — one bright finance subject across several art styles.
// Invalid substyles just 400 and are skipped (their names get logged).
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

// Bright, light, cheerful palette (a lift from the dull muted set).
const COLORS = [
  { rgb: [236, 243, 239], weight: 0.24 }, // mist
  { rgb: [85, 195, 116], weight: 0.24 }, // signal green (brighter)
  { rgb: [20, 113, 95], weight: 0.16 }, // lichen
  { rgb: [180, 168, 214], weight: 0.16 }, // soft periwinkle
  { rgb: [206, 224, 236], weight: 0.1 }, // pale sky
];

// A finance + growth + optimism subject, simple enough to read in any style.
const SUBJECT =
  "a small fresh green seedling sprouting and growing upward out of a neat stack of round coins, " +
  "gentle bright morning light, a few leaves unfurling; hopeful, uplifting and optimistic; steady growth and investing";

const TONE = "bright, light, airy, cheerful and optimistic, clean, generous space, no text, no words, no logos";

// name -> request shape. V4.1 Pro is prompt-only (no style/substyle).
const CONFIGS = [
  { name: "watercolor", model: "recraftv3", style: "digital_illustration", substyle: "watercolor", desc: "soft loose watercolor painting, gentle translucent washes, paper texture" },
  { name: "hand_drawn", model: "recraftv3", style: "digital_illustration", substyle: "hand_drawn", desc: "warm hand-drawn illustration, soft pencil and crayon, friendly" },
  { name: "line_art", model: "recraftv3", style: "vector_illustration", substyle: "line_art", desc: "clean fine single-weight ink line drawing, minimal and editorial" },
  { name: "engraving", model: "recraftv3", style: "digital_illustration", substyle: "engraving_color", desc: "fine cross-hatched pen-and-ink engraving, plotter-like hatched shading" },
  { name: "pastel", model: "recraftv3", style: "digital_illustration", substyle: "pastel_gradient", desc: "bright soft pastel with smooth light gradients, airy" },
  { name: "flat_digital", model: "recraftv3", style: "digital_illustration", substyle: "2d_art_poster", desc: "clean bright modern flat digital illustration, crisp shapes" },
  { name: "v41pro_watercolor", model: "recraftv4_1_pro", size: "2048x2048", desc: "a soft loose watercolor painting with gentle translucent washes and visible paper texture" },
];

const outDir = path.join(HERE, "styles");
await fs.mkdir(outDir, { recursive: true });

const only = process.argv.slice(2);
for (const c of CONFIGS) {
  if (only.length && !only.includes(c.name)) continue;
  const body = {
    prompt: `${SUBJECT}. ${c.desc}. ${TONE}.`,
    model: c.model,
    size: c.size || "1024x1024",
    n: 1,
    response_format: "url",
    controls: { colors: COLORS },
  };
  if (c.style) body.style = c.style;
  if (c.substyle) body.substyle = c.substyle;
  const res = await fetch("https://external.api.recraft.ai/v1/images/generations", {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) { console.error(`[${c.name}] HTTP ${res.status} ${JSON.stringify(json).slice(0, 200)}`); continue; }
  const url = json?.data?.[0]?.url;
  if (!url) { console.error(`[${c.name}] no url`); continue; }
  const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
  await fs.writeFile(path.join(outDir, `${c.name}.png`), buf);
  console.log(`[${c.name}] saved (${buf.length} bytes)`);
}
