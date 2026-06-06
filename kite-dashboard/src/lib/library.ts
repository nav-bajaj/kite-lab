import fs from "node:fs";
import path from "node:path";

export type LibraryAsset = {
  type: "thumbnail" | "carousel" | "reel" | "other";
  path: string;
  filename: string;
  alt: string;
};

export type LibraryHookVariant = {
  text: string;
  style: string;
};

export type LibraryPiece = {
  slug: string;
  title: string;
  pillar: string;
  format: string;
  duration: string;
  published_at: string;
  hook: string;
  alternate_hooks: LibraryHookVariant[];
  body: string[];
  key_takeaway: string;
  contrarian_angle: string;
  cta: string;
  assets: LibraryAsset[];
  meta: {
    signal_type?: string;
    source_repo?: string;
    source_signal?: string;
    data_points?: string[];
    confidence?: string;
    compliance_summary?: string;
  };
};

export type LibraryManifestEntry = {
  slug: string;
  title: string;
  pillar: string;
  format: string;
  published_at: string;
  thumbnail: string | null;
  hook: string;
};

export type LibraryManifest = {
  pieces: LibraryManifestEntry[];
  last_updated: string | null;
};

const CONTENT_ROOT = path.join(process.cwd(), "src", "marketing-content");
const MANIFEST_PATH = path.join(CONTENT_ROOT, "manifest.json");
const PIECES_DIR = path.join(CONTENT_ROOT, "pieces");

// File-path arguments below come from `slug` values that the build
// itself emits into `marketing-content/manifest.json` via the content
// repo's `scripts/publish.py`. They are never user-controlled at
// runtime — these routes are static-generated at build time and the
// reads only happen inside `getStaticParams` / page render. The eslint
// `security/detect-non-literal-fs-filename` warning is therefore a
// false positive in this context.

export function getManifest(): LibraryManifest {
  if (!fs.existsSync(MANIFEST_PATH)) {
    return { pieces: [], last_updated: null };
  }
  return JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8")) as LibraryManifest;
}

export function getAllSlugs(): string[] {
  return getManifest().pieces.map((p) => p.slug);
}

export function getPiece(slug: string): LibraryPiece | null {
  const piecePath = path.join(PIECES_DIR, `${slug}.json`);
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see rationale above
  if (!fs.existsSync(piecePath)) {
    return null;
  }
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- see rationale above
  return JSON.parse(fs.readFileSync(piecePath, "utf8")) as LibraryPiece;
}

export function groupByPillar(
  entries: LibraryManifestEntry[]
): Map<string, LibraryManifestEntry[]> {
  const groups = new Map<string, LibraryManifestEntry[]>();
  for (const entry of entries) {
    const key = entry.pillar || "uncategorised";
    const bucket = groups.get(key);
    if (bucket) {
      bucket.push(entry);
    } else {
      groups.set(key, [entry]);
    }
  }
  return groups;
}
