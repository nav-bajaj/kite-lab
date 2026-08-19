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
    <article className="mx-auto flex max-w-[720px] flex-col gap-7">
      <nav className="text-xs text-muted-foreground">
        <Link href="/insights/learn" className="underline-offset-2 hover:text-foreground hover:underline">
          Learn
        </Link>
        {" · "}
        <span className="uppercase tracking-wide">{explainer.category}</span>
      </nav>

      <header className="flex flex-col gap-3 border-b border-border pb-6">
        <h2 className="text-[2rem] font-semibold leading-[1.1] tracking-[-0.02em] text-foreground">
          {explainer.title}
        </h2>
        <p className="text-lg leading-[1.6] text-muted-foreground">{explainer.summary}</p>
        <p className="text-xs text-muted-foreground">
          Last reviewed {explainer.lastUpdated}
        </p>
      </header>

      <div className="flex flex-col gap-8">
        {explainer.sections.map((s) => (
          <section key={s.heading} className="flex flex-col gap-2">
            <h3 className="text-lg font-semibold tracking-[-0.01em] text-foreground">
              {s.heading}
            </h3>
            <RenderBody body={s.body} />
          </section>
        ))}
      </div>

      {related.length > 0 && (
        <aside className="mt-4 flex flex-col gap-2 border-t border-border pt-6 text-sm">
          <p className="font-medium text-foreground">Related explainers</p>
          <ul className="flex flex-wrap gap-2">
            {related.map((r) => (
              <li key={r.slug}>
                <Link
                  href={`/insights/learn/${r.slug}`}
                  className="rounded-lg border border-border px-3 py-1.5 text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                >
                  {r.title}
                </Link>
              </li>
            ))}
          </ul>
        </aside>
      )}

      <p className="text-xs text-muted-foreground">
        Educational content, not investment advice. Examples are illustrative —
        past patterns do not guarantee future outcomes.
      </p>
    </article>
  );
}
