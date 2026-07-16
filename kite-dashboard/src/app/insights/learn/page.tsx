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
    blurb: "What each number measures, and how to read it.",
  },
  {
    key: "pattern",
    label: "Patterns",
    blurb: "The chart setups we point out and what they tend to mean.",
  },
  {
    key: "concept",
    label: "Concepts",
    blurb: "The big ideas the whole platform is built on.",
  },
];

export default function LearnIndexPage() {
  const byCat = explainersByCategory();
  return (
    <main className="flex flex-col gap-10">
      <header className="flex flex-col gap-2">
        <h2 className="font-serif text-2xl font-medium tracking-[-0.01em] text-foreground">
          Learn
        </h2>
        <p className="max-w-2xl text-[15px] leading-[1.6] text-muted-foreground">
          Short, plain-English explainers for every term we use. New to this?
          Start here. And anywhere you see a &ldquo;What is this?&rdquo; link on
          the dashboard, it brings you back to the right explainer.
        </p>
      </header>

      {/* Glossary featured card */}
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-card p-6">
        <div className="flex flex-col gap-1">
          <h3 className="font-serif text-lg font-medium tracking-[-0.01em] text-foreground">
            Glossary
          </h3>
          <p className="text-[13px] leading-[1.5] text-muted-foreground">
            {GLOSSARY.length} quick definitions — every term in one place, in
            one line each.
          </p>
        </div>
        <Link
          href="/insights/learn/glossary"
          className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:border-primary/40"
        >
          Open glossary →
        </Link>
      </section>

      {CATEGORY_ORDER.map((cat) => {
        const items = byCat[cat.key] ?? [];
        if (items.length === 0) return null;
        return (
          <section key={cat.key} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <h3 className="font-serif text-lg font-medium tracking-[-0.01em] text-foreground">
                {cat.label}
              </h3>
              <p className="text-[13px] text-muted-foreground">{cat.blurb}</p>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {items.map((e) => (
                <li key={e.slug}>
                  <Link
                    href={`/insights/learn/${e.slug}`}
                    className="flex h-full flex-col gap-1 rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/40"
                  >
                    <p className="font-medium text-foreground">{e.title}</p>
                    <p className="text-[13px] leading-[1.5] text-muted-foreground">
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
