import Link from "next/link";
import type { Metadata } from "next";

import {
  GLOSSARY,
  BUCKET_LABELS,
  type GlossaryEntry,
} from "@/content/insights/learn/glossary/_data";

export const metadata: Metadata = {
  title: "Glossary — Marketworks Insights",
  description:
    "Plain-English definitions of the indicators, patterns, and terms used on Marketworks Insights.",
};

const BUCKET_ORDER: GlossaryEntry["bucket"][] = [
  "market-state",
  "breadth-momentum",
  "patterns",
  "math",
  "flows-structure",
  "general",
];

export default function GlossaryPage() {
  const byBucket = BUCKET_ORDER.map((b) => ({
    bucket: b,
    entries: GLOSSARY.filter((e) => e.bucket === b).sort((a, b) =>
      a.term.localeCompare(b.term),
    ),
  }));

  const totalEntries = GLOSSARY.length;

  return (
    <main className="space-y-8">
      <header className="space-y-2">
        <nav className="text-xs text-neutral-500">
          <Link href="/insights/learn" className="underline-offset-2 hover:underline">
            Learn
          </Link>
          {" · Glossary"}
        </nav>
        <h2 className="text-lg font-semibold">Glossary</h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          {totalEntries} terms used across the dashboard, grouped by topic.
          Where a term has a deep-dive explainer, the link takes you there.
        </p>
      </header>

      {/* Section nav — clickable buckets anchor down the page */}
      <nav className="flex flex-wrap gap-2 text-xs">
        {byBucket.map(({ bucket, entries }) => (
          <a
            key={bucket}
            href={`#${bucket}`}
            className="rounded border px-2 py-1 hover:bg-neutral-100 dark:hover:bg-neutral-900"
          >
            {/* eslint-disable-next-line security/detect-object-injection */}
            {BUCKET_LABELS[bucket]} ({entries.length})
          </a>
        ))}
      </nav>

      {byBucket.map(({ bucket, entries }) => (
        <section
          key={bucket}
          id={bucket}
          className="space-y-4 scroll-mt-20"
        >
          <h3 className="border-b pb-1 text-base font-semibold">
            {/* eslint-disable-next-line security/detect-object-injection */}
            {BUCKET_LABELS[bucket]}
          </h3>
          <dl className="space-y-4">
            {entries.map((e) => (
              <div key={e.anchor} id={e.anchor} className="scroll-mt-20">
                <dt className="font-medium">
                  {e.term}
                  {e.related && (
                    <Link
                      href={`/insights/learn/${e.related}`}
                      className="ml-2 text-xs text-neutral-500 underline-offset-2 hover:underline"
                    >
                      deep-dive →
                    </Link>
                  )}
                </dt>
                <dd className="mt-1 text-sm text-neutral-700 dark:text-neutral-300">
                  {e.definition}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}

      <p className="border-t pt-4 text-xs text-neutral-500">
        Missing a term?{" "}
        <Link href="/insights/learn" className="underline-offset-2 hover:underline">
          Back to Learn index
        </Link>
        .
      </p>
    </main>
  );
}
