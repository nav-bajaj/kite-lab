/**
 * Learn explainer content types.
 *
 * Authoring convention: one TS file per topic under
 * `kite-dashboard/src/content/insights/learn/<slug>.ts`. Each exports a
 * typed `LearnExplainer` object. The barrel `_index.ts` aggregates them
 * into a single registry that the loader (`lib/learn-content.ts`) and the
 * route (`app/insights/learn/[topic]/page.tsx`) consume.
 *
 * Body strings support minimal inline markup:
 *   **bold**           → <strong>
 *   _italic_           → <em>
 *   [text](url)        → <a>
 *   - list items       → <ul>/<li>
 *   `code`             → <code>
 * Paragraphs are split on blank lines (`\n\n`). See `_render.tsx`.
 */

export type LearnCategory = "indicator" | "pattern" | "concept" | "glossary";

export type LearnSection = {
  heading: string;
  body: string;
};

export type LearnExplainer = {
  slug: string;
  title: string;
  category: LearnCategory;
  /** One-line summary used on index cards + page meta description. */
  summary: string;
  /** Other slugs in this registry that complement this one. */
  related?: string[];
  /** Body sections. Convention: What it is / Why it matters / How to read. */
  sections: LearnSection[];
  /** ISO date the content was last reviewed. */
  lastUpdated: string;
};
