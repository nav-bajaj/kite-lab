// Clean modern fintech set via Higgsfield Nano Banana Pro (1k). Submit all, poll, download.
// Reuses nano_test.png (the polished sprout-from-coins) as hero; generates the other 5.
import { execFileSync } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const hf = (args) =>
  execFileSync("higgsfield", args, { encoding: "utf8", maxBuffer: 20 * 1024 * 1024 });

// The style that produced the polished, modern, "fintechy" nano_test.
const STYLE =
  "Clean modern illustration with smooth soft gradients, glossy and polished, a friendly modern fintech " +
  "style, crisp light and airy with subtle depth. Cool brand palette only: fresh green (#55C374 and deep " +
  "#14715F), mist off-white (#ECF3EF), soft lavender, pale sky blue; NO warm rust, orange, red or brown; " +
  "bright, light and clean, lots of soft negative space. No text, no words, no logos.";

const JOBS = {
  rank: "Three or four simple rounded pillars of clearly increasing height, like a tidy stepped skyline, with a small fresh green leaf resting on the single tallest one; ranking the strongest, minimal and clean.",
  build: "A gentle hand neatly stacking a few round coins into one tidy pile, a small green sprout growing from the top of the stack; assembling a portfolio, simple and clean.",
  follow: "A single smartphone standing upright, its screen showing one gentle smooth upward line and a small green leaf, a soft glow around it; following along, clean and modern.",
  research: "A clean magnifying glass hovering over a small card showing one simple smooth rising line and a tiny green leaf; careful study, minimal and modern.",
  portfolios: "Three simple rounded cards standing side by side in a neat row, each holding a small different green plant motif; three portfolios, clean and minimal.",
};

const outDir = path.join(HERE, "set_hf_fintech");
await fs.mkdir(outDir, { recursive: true });
try { await fs.copyFile(path.join(HERE, "hf_test/nano_test.png"), path.join(outDir, "hero.png")); } catch {}

const ids = {};
for (const [n, subj] of Object.entries(JOBS)) {
  try {
    const out = hf(["generate", "create", "nano_banana_pro", "--prompt", `${subj} ${STYLE}`, "--aspect-ratio", "1:1", "--resolution", "1k", "--json"]);
    const id = (out.match(/"id":\s*"([0-9a-f-]{36})"/) || [])[1];
    ids[n] = id;
    console.log(`submitted ${n} -> ${id || "NO ID"}`);
  } catch (e) {
    console.log(`submit ${n} failed: ${String(e).split("\n")[0]}`);
  }
}

for (const [n, id] of Object.entries(ids)) {
  if (!id) continue;
  let done = false;
  for (let i = 0; i < 150 && !done; i++) {
    let url = "";
    try { url = (hf(["generate", "get", id, "--json"]).match(/https:\/\/[^"]+\.png[^"]*/) || [])[0] || ""; } catch {}
    if (url) {
      const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
      await fs.writeFile(path.join(outDir, `${n}.png`), buf);
      console.log(`${n} done`);
      done = true;
    } else {
      await new Promise((r) => setTimeout(r, 15000));
    }
  }
  if (!done) console.log(`${n}: timed out waiting`);
}
console.log("batch done");
