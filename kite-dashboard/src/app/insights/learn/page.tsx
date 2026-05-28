import Link from "next/link";
import type { Metadata } from "next";

import { explainersByCategory } from "@/lib/learn-content";
import { GLOSSARY } from "@/content/insights/learn/glossary/_data";

export const metadata: Metadata = {
  title: "Learn — Marketworks Insights",
  description:
    "Plain-English explainers for every indicator, pattern, and concept used on Marketworks Insights.",
};

const CATEGORY_ORDER: Array<{
  key: string;
  label: string;
  blurb: string;
}> = [
  {
    key: "indicator",
    label: "Indicators",
    blurb: "What each indicator measures and how to read it.",
  },
  {
    key: "pattern",
    label: "Patterns",
    blurb: "Technical setups we surface on the Watchlists page.",
  },
  {
    key: "concept",
    label: "Concepts",
    blurb: "Foundational ideas referenced throughout the platform.",
  },
];

export default function LearnIndexPage() {
  const byCat = explainersByCategory();
  return (
    <main className="space-y-8">
      <header>
        <h2 className="text-lg font-semibold">Learn</h2>
        <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
          Short, plain-English explainers for every indicator, pattern, and
          concept we use. Every reading on the dashboard links back here —
          if you don&apos;t recognise a term, this is where you look.
        </p>
      </header>

      {/* Glossary featured card — drives traffic to the term reference */}
      <section className="rounded border bg-neutral-50 p-4 dark:bg-neutral-900/50">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h3 className="text-base font-semibold">Glossary</h3>
            <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">
              {GLOSSARY.length} short definitions across market state,
              breadth, patterns, math, flows, and general terms.
            </p>
          </div>
          <Link
            href="/insights/learn/glossary"
            className="rounded border bg-white px-3 py-1 text-sm hover:bg-neutral-100 dark:bg-neutral-950 dark:hover:bg-neutral-800"
          >
            Open glossary →
          </Link>
        </div>
      </section>

      {CATEGORY_ORDER.map((cat) => {
        const items = byCat[cat.key] ?? [];
        if (items.length === 0) return null;
        return (
          <section key={cat.key} className="space-y-3">
            <div>
              <h3 className="text-base font-semibold">{cat.label}</h3>
              <p className="text-xs text-neutral-500">{cat.blurb}</p>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {items.map((e) => (
                <li key={e.slug}>
                  <Link
                    href={`/insights/learn/${e.slug}`}
                    className="block rounded border p-3 hover:bg-neutral-50 dark:hover:bg-neutral-900"
                  >
                    <p className="font-medium">{e.title}</p>
                    <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">
                      {e.summary}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </main>
  );
}
