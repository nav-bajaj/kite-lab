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
    <main className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <nav className="text-xs text-muted-foreground">
          <Link href="/insights/learn" className="underline-offset-2 hover:text-foreground hover:underline">
            Learn
          </Link>
          {" · Glossary"}
        </nav>
        <h2 className="text-2xl font-semibold tracking-[-0.01em] text-foreground">
          Glossary
        </h2>
        <p className="max-w-2xl text-[15px] leading-[1.6] text-muted-foreground">
          {totalEntries} terms used across Insights, one line each, grouped by
          topic. Where a term has a fuller explainer, the link takes you there.
        </p>
      </header>

      {/* Section nav — clickable buckets anchor down the page */}
      <nav className="flex flex-wrap gap-2 text-xs">
        {byBucket.map(({ bucket, entries }) => (
          <a
            key={bucket}
            href={`#${bucket}`}
            className="rounded-lg border border-border px-3 py-1.5 font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
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
          className="flex flex-col gap-4 scroll-mt-24"
        >
          <h3 className="border-b border-border pb-2 text-lg font-semibold tracking-[-0.01em] text-foreground">
            {/* eslint-disable-next-line security/detect-object-injection */}
            {BUCKET_LABELS[bucket]}
          </h3>
          <dl className="flex flex-col gap-4">
            {entries.map((e) => (
              <div key={e.anchor} id={e.anchor} className="scroll-mt-24">
                <dt className="font-medium text-foreground">
                  {e.term}
                  {e.related && (
                    <Link
                      href={`/insights/learn/${e.related}`}
                      className="ml-2 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                    >
                      deep-dive →
                    </Link>
                  )}
                </dt>
                <dd className="mt-1 text-[14px] leading-[1.55] text-muted-foreground">
                  {e.definition}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}

      <p className="border-t border-border pt-4 text-xs text-muted-foreground">
        Missing a term?{" "}
        <Link href="/insights/learn" className="underline-offset-2 hover:text-foreground hover:underline">
          Back to Learn index
        </Link>
        .
      </p>
    </main>
  );
}
