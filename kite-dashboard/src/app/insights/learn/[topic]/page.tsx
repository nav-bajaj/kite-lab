import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";

import { getExplainer, listExplainerSlugs } from "@/lib/learn-content";
import { RenderBody } from "@/content/insights/learn/_render";

export function generateStaticParams() {
  return listExplainerSlugs().map((topic) => ({ topic }));
}

export async function generateMetadata(
  { params }: { params: Promise<{ topic: string }> },
): Promise<Metadata> {
  const { topic } = await params;
  const e = getExplainer(topic);
  if (!e) return { title: "Not found — Marketworks Insights" };
  return {
    title: `${e.title} — Marketworks Insights`,
    description: e.summary,
  };
}

export default async function LearnTopicPage(
  { params }: { params: Promise<{ topic: string }> },
) {
  const { topic } = await params;
  const explainer = getExplainer(topic);
  if (!explainer) notFound();

  const related = (explainer.related ?? [])
    .map((s) => getExplainer(s))
    .filter((e): e is NonNullable<typeof e> => Boolean(e));

  return (
    <article className="space-y-6">
      <nav className="text-xs text-neutral-500">
        <Link href="/insights/learn" className="underline-offset-2 hover:underline">
          Learn
        </Link>
        {" · "}
        <span className="uppercase tracking-wide">{explainer.category}</span>
      </nav>

      <header className="space-y-2 border-b pb-4">
        <h2 className="text-2xl font-semibold">{explainer.title}</h2>
        <p className="text-neutral-600 dark:text-neutral-400">{explainer.summary}</p>
        <p className="text-xs text-neutral-500">
          Last reviewed {explainer.lastUpdated}
        </p>
      </header>

      <div className="space-y-8">
        {explainer.sections.map((s) => (
          <section key={s.heading}>
            <h3 className="mb-2 text-base font-semibold">{s.heading}</h3>
            <RenderBody body={s.body} />
          </section>
        ))}
      </div>

      {related.length > 0 && (
        <aside className="mt-10 border-t pt-4 text-sm">
          <p className="mb-2 font-medium">Related explainers</p>
          <ul className="flex flex-wrap gap-2">
            {related.map((r) => (
              <li key={r.slug}>
                <Link
                  href={`/insights/learn/${r.slug}`}
                  className="rounded border px-2 py-1 hover:bg-neutral-100 dark:hover:bg-neutral-900"
                >
                  {r.title}
                </Link>
              </li>
            ))}
          </ul>
        </aside>
      )}

      <p className="text-xs text-neutral-500">
        Educational content; not investment advice. Methodology and
        examples are illustrative — past patterns do not guarantee future
        outcomes.
      </p>
    </article>
  );
}
