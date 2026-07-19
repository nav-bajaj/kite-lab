// Optimize the curated picks -> web webp, self-hosted under kite-dashboard/public.
import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const sharp = require("/Users/navdeep/kite-lab/kite-dashboard/node_modules/sharp");

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(HERE, "set_hf_fintech");
const OUT = "/Users/navdeep/kite-lab/kite-dashboard/public/illustrations";
await fs.mkdir(OUT, { recursive: true });

// Clean fintech set (Higgsfield Nano Banana Pro). New `fin-` prefix so the
// dev/browser cache serves them fresh, not the old muted webp.
const PICKS = {
  hero: "hero.png",
  rank: "rank.png",
  build: "build.png",
  follow: "follow.png",
  research: "research.png",
  portfolios: "portfolios.png",
};

for (const [name, file] of Object.entries(PICKS)) {
  const outFile = path.join(OUT, `fin-${name}.webp`);
  await sharp(path.join(SRC, file))
    .resize(900, 900, { fit: "cover" })
    .webp({ quality: 82 })
    .toFile(outFile);
  const { size } = await fs.stat(outFile);
  console.log(`fin-${name}.webp  ${(size / 1024).toFixed(0)} KB`);
}
