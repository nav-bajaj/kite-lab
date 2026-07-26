// Muted pastel/crayon grain test — desaturated, hazy, varied compositions.
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

// COOL muted palette only — no warm at all; pale, faded, low-contrast.
const COLORS = [
  { rgb: [236, 243, 239], weight: 0.26 }, // mist off-white
  { rgb: [160, 186, 170], weight: 0.26 }, // soft faded sage
  { rgb: [88, 132, 118], weight: 0.16 }, // faded teal (dusty lichen)
  { rgb: [178, 164, 198], weight: 0.16 }, // soft dusty lavender
  { rgb: [90, 90, 96], weight: 0.12 }, // soft cool charcoal (not pure ink)
];

const STYLE =
  "soft muted pastel illustration, grainy soft-crayon and colored-pencil texture on textured paper, fine " +
  "gentle grain, HAZY and washed-out with soft edges, VERY LOW SATURATION, faded desaturated pale dusty " +
  "tones, quiet dreamy and calm, low contrast, generous negative space, contemplative editorial op-ed " +
  "illustration in the quiet misty mood of Matija Medved, metaphorical not literal, no text, no words, no " +
  "logos. COOL muted palette only: soft sage green, pale mist off-white, faded teal, soft dusty lavender " +
  "and soft charcoal grey; NO warm colours, NO yellow, NO orange, NO gold, NO bright or saturated colours; " +
  "pale, gentle, low-contrast and washed-out";

const JOBS = {
  hero: "a person standing quietly at a large window at dawn, seen from inside a calm room, looking out at a soft pale sky over distant gentle hills; unhurried and contemplative",
  rank: "a row of tall slender glass bottles of clearly different heights on a windowsill, the single tallest one softly catching the light; standing out among many",
  research: "a magnifying glass resting on an open notebook covered in faint handwriting on a wooden desk in soft morning light; patient careful study",
};

const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(JOBS);
const outDir = path.join(HERE, "pastel2");
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
      n: 1,
      response_format: "url",
      controls: { colors: COLORS },
    }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) { console.error(`[${name}] HTTP ${res.status}`, JSON.stringify(json).slice(0, 400)); continue; }
  const url = json?.data?.[0]?.url;
  if (!url) { console.error(`[${name}] no url`, JSON.stringify(json).slice(0, 300)); continue; }
  const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
  await fs.writeFile(path.join(outDir, `${name}.png`), buf);
  console.log(`[${name}] saved (${buf.length} bytes)`);
}
