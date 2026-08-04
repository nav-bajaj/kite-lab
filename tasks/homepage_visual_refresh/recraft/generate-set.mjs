// Full-set generator for a given style. node generate-set.mjs <style> [subject...]
// styles: watercolor (V4.1 Pro) | pastel (V3) | engraving (V3)
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
  { rgb: [85, 195, 116], weight: 0.22 }, // fresh green
  { rgb: [20, 113, 95], weight: 0.12 }, // lichen
  { rgb: [180, 168, 214], weight: 0.14 }, // soft periwinkle
  { rgb: [206, 224, 236], weight: 0.14 }, // pale sky
  { rgb: [245, 232, 205], weight: 0.18 }, // soft warm sunlight
];

const STYLES = {
  watercolor: { model: "recraftv4_1_pro", size: "2048x2048", desc: "A soft loose watercolor painting with gentle translucent washes and visible paper texture, delicate airy and luminous" },
  pastel: { model: "recraftv3", style: "digital_illustration", substyle: "pastel_gradient", size: "1024x1024", desc: "Soft bright pastel illustration with smooth light gradients, airy and clean" },
  engraving: { model: "recraftv3", style: "digital_illustration", substyle: "engraving_color", size: "1024x1024", desc: "Fine cross-hatched pen-and-ink engraving with plotter-like hatched line shading, editorial" },
};

const TONE = "bright, light, hopeful, optimistic, calm, fresh, generous space, no text, no words, no logos";

const JOBS = {
  hero: "a calm person tending a cluster of small green plants growing upward from the earth in bright soft morning light; unhurried, quietly hopeful, steady growth",
  rank: "several slender young trees of clearly different heights on a gentle sunlit hill, all reaching upward toward a bright sun, the tallest catching the most light; rising strength",
  build: "a pair of gentle hands carefully gathering a few of the ripest round fruits from a leafy branch into a small woven basket; choosing only the best few",
  follow: "a small figure walking along a bright winding sunlit path curving forward over gentle green hills toward the horizon; a clear hopeful route to follow",
  research: "a bright sunlit wooden desk beside a window with an open notebook of faint handwriting, a magnifying glass and a small potted plant; patient hopeful study",
  portfolios: "three healthy potted plants of clearly different character standing side by side in bright soft light; three distinct temperaments",
};

const styleName = process.argv[2];
const cfg = STYLES[styleName];
if (!cfg) { console.error("usage: node generate-set.mjs <watercolor|pastel|engraving> [subject...]"); process.exit(1); }
const names = process.argv.slice(3).length ? process.argv.slice(3) : Object.keys(JOBS);
const outDir = path.join(HERE, `set_${styleName}`);
await fs.mkdir(outDir, { recursive: true });

for (const name of names) {
  const subject = JOBS[name];
  if (!subject) { console.error(`unknown job: ${name}`); continue; }
  const body = {
    prompt: `${subject}. ${cfg.desc}. ${TONE}.`,
    model: cfg.model,
    size: cfg.size,
    n: 1,
    response_format: "url",
    controls: { colors: COLORS },
  };
  if (cfg.style) body.style = cfg.style;
  if (cfg.substyle) body.substyle = cfg.substyle;
  const res = await fetch("https://external.api.recraft.ai/v1/images/generations", {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) { console.error(`[${styleName}/${name}] HTTP ${res.status}`, JSON.stringify(json).slice(0, 200)); continue; }
  const url = json?.data?.[0]?.url;
  if (!url) { console.error(`[${styleName}/${name}] no url`); continue; }
  const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
  await fs.writeFile(path.join(outDir, `${name}.png`), buf);
  console.log(`[${styleName}/${name}] saved (${buf.length} bytes)`);
}
