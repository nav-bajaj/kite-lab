// Full pastel set via Higgsfield Nano Banana Pro. Submit all, poll, download.
// Reuses the great hero/research tests; generates rank/build/follow/portfolios.
import { execFileSync } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const hf = (args) =>
  execFileSync("higgsfield", args, { encoding: "utf8", maxBuffer: 20 * 1024 * 1024 });

const STYLE =
  "Soft matte chalk-pastel illustration, hand-painted with a gentle grainy paper texture, soft brush " +
  "strokes, flat airy muted and calm, NOT glossy, NOT 3D, NOT a shiny vector icon. Cool brand palette only: " +
  "soft sage and fresh green, mist off-white, soft lavender, pale sky blue; no warm rust orange red or brown; " +
  "bright light and cheerful, lots of soft negative space. No text, no words, no logos.";

const JOBS = {
  rank: "Several slender young trees of clearly different heights growing on a gentle green hill in soft bright morning light, all reaching upward, the tallest catching the most light; rising strength and growth.",
  build: "A pair of gentle hands carefully gathering a few of the ripest round fruits from a leafy branch into a small woven basket in soft morning light; choosing only the best few.",
  follow: "A small figure seen from behind walking along a bright winding path over gentle green hills toward a soft bright horizon in soft morning light; a clear hopeful route to follow.",
  portfolios: "Three healthy potted plants of clearly different character standing side by side on a bright windowsill in soft morning light; three distinct temperaments.",
};

const outDir = path.join(HERE, "set_hf_pastel");
await fs.mkdir(outDir, { recursive: true });

// Reuse the two great test images.
for (const [src, dst] of [["hf_test/nano_hero.png", "hero.png"], ["hf_test/nano_research.png", "research.png"]]) {
  try { await fs.copyFile(path.join(HERE, src), path.join(outDir, dst)); } catch {}
}

// Submit all remaining jobs.
const ids = {};
for (const [n, subj] of Object.entries(JOBS)) {
  try {
    const out = hf(["generate", "create", "nano_banana_pro", "--prompt", `${subj} ${STYLE}`, "--aspect-ratio", "1:1", "--resolution", "2k", "--json"]);
    const id = (out.match(/"id":\s*"([0-9a-f-]{36})"/) || [])[1];
    ids[n] = id;
    console.log(`submitted ${n} -> ${id || "NO ID"}`);
  } catch (e) {
    console.log(`submit ${n} failed: ${String(e).split("\n")[0]}`);
  }
}

// Poll each until it yields a PNG url, then download.
for (const [n, id] of Object.entries(ids)) {
  if (!id) continue;
  let done = false;
  for (let i = 0; i < 120 && !done; i++) {
    let url = "";
    try { url = (hf(["generate", "get", id, "--json"]).match(/https:\/\/[^"]+\.png[^"]*/) || [])[0] || ""; } catch {}
    if (url) {
      const buf = Buffer.from(await (await fetch(url)).arrayBuffer());
      await fs.writeFile(path.join(outDir, `${n}.png`), buf);
      console.log(`${n} done`);
      done = true;
    } else {
      await new Promise((r) => setTimeout(r, 20000));
    }
  }
  if (!done) console.log(`${n}: timed out waiting`);
}
console.log("batch done");
