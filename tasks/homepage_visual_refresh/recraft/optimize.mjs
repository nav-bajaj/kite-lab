// Optimize the curated picks -> web webp, self-hosted under kite-dashboard/public.
import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const sharp = require("/Users/navdeep/kite-lab/kite-dashboard/node_modules/sharp");

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(HERE, "final");
const OUT = "/Users/navdeep/kite-lab/kite-dashboard/public/illustrations";
await fs.mkdir(OUT, { recursive: true });

// curated pick per slot
const PICKS = {
  hero: "hero_1.png",
  rank: "rank_1.png",
  build: "build_1.png",
  follow: "follow_1.png",
  research: "research_1.png",
  portfolios: "portfolios_1.png",
};

for (const [name, file] of Object.entries(PICKS)) {
  const outFile = path.join(OUT, `${name}.webp`);
  await sharp(path.join(SRC, file))
    .resize(900, 900, { fit: "cover" })
    .webp({ quality: 80 })
    .toFile(outFile);
  const { size } = await fs.stat(outFile);
  console.log(`${name}.webp  ${(size / 1024).toFixed(0)} KB`);
}
