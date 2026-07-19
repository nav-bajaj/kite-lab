// Composition round — clearer metaphors, verbose prompts, locked cool-muted style.
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

// Locked COOL muted palette (round 3).
const COLORS = [
  { rgb: [236, 243, 239], weight: 0.26 }, // mist off-white
  { rgb: [160, 186, 170], weight: 0.26 }, // soft faded sage
  { rgb: [88, 132, 118], weight: 0.16 }, // faded teal
  { rgb: [178, 164, 198], weight: 0.16 }, // soft dusty lavender
  { rgb: [90, 90, 96], weight: 0.12 }, // soft cool charcoal
];

const STYLE =
  "Soft muted pastel op-ed illustration; grainy soft-crayon and colored-pencil texture, hazy and washed-out, " +
  "very low saturation, faded pale dusty low-contrast tones, quiet and dreamy, generous negative space, " +
  "metaphorical, misty Matija-Medved mood. COOL muted palette only: soft sage, pale mist, faded teal, dusty " +
  "lavender, soft charcoal; NO warm, no yellow/orange/gold/red/brown, nothing saturated. No text, no logos.";

const JOBS = {
  hero:
    "A single small calm figure standing at a large window inside a quiet empty room at dawn, seen from " +
    "behind, gazing out at a wide valley of soft layered misty hills rolling to a pale distant horizon. " +
    "Unhurried and patient, in no rush, simply watching. Lots of quiet empty space around the small figure.",
  rank:
    "Several simple rounded hot-air balloons drifting slowly upward at clearly different heights over a soft " +
    "misty valley at dawn, across a wide pale sky. One balloon has risen highest of all and gently catches " +
    "the first faint light, clearly above the others. The ones with the most lift rising quietly to the top.",
  build:
    "A pair of gentle hands reaching up into the leafy branches of a small tree, carefully picking only a " +
    "few of the ripest round deep-purple plums and gathering them into a simple woven basket held below, " +
    "leaving the smaller unripe fruit on the branch. Choosing only the best few. Soft, patient, quiet.",
  follow:
    "A small lone figure seen from behind walking calmly along a gently winding footpath that curves away " +
    "over soft low misty hills toward a faint marker on the distant horizon. The path is lined on both sides " +
    "by a row of small evenly spaced glowing lanterns lighting the way. A clear route to follow, no guessing.",
  research:
    "A large round magnifying glass held in a still hand over the pale, light cut cross-section of an old " +
    "tree stump on a plain light wooden desk in soft airy morning light, its many fine concentric growth " +
    "rings revealed softly beneath the lens. Reading decades of quiet history, ring by ring. Light and calm.",
  portfolios:
    "Three small potted plants of clearly different character standing evenly spaced side by side on a plain " +
    "windowsill in soft, even light: one tall and reaching upward, one low and rounded and steady, one " +
    "delicate with fine slender leaves. Three distinct temperaments sharing one quiet shelf. Simple, balanced, calm.",
};

const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(JOBS);
const outDir = path.join(HERE, "finalset");
await fs.mkdir(outDir, { recursive: true });

for (const name of names) {
  const subject = JOBS[name];
  if (!subject) { console.error(`unknown job: ${name}`); continue; }
  const res = await fetch("https://external.api.recraft.ai/v1/images/generations", {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: `${subject} ${STYLE}.`,
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
