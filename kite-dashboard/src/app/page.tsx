import Link from "next/link";

import { UNIVERSES } from "@/lib/universes";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { PortfolioCard } from "@/components/marketing/portfolio-card";

export const metadata = {
  title: "Marketworks — Indian markets, the calm way",
  description:
    "Momentum-based model portfolios and a daily insight engine for Indian " +
    "equities, grounded in live market data. Currently in private beta.",
};

const FEATURES = [
  {
    title: "Four model portfolios",
    body: "Momentum strategies on Indian equities, rebalanced on a system — not on gut or headlines.",
  },
  {
    title: "A daily insight engine",
    body: "Sector leadership, market regime, and stress — the same readings our portfolios run on, published daily.",
  },
  {
    title: "Grounded in our own data",
    body: "Every read traces back to live market data and our own holdings. No recycled opinions about other people's books.",
  },
];

export default function LandingPage() {
  const portfolios = Object.values(UNIVERSES).filter((u) => u.clientVisible);

  return (
    <div className="mw-brand flex min-h-screen flex-col bg-background">
      <MarketingNav />

      <main className="flex-1">
        {/* Hero */}
        <section className="px-6 py-24 sm:px-12 sm:py-32">
          <div className="mx-auto flex max-w-[880px] flex-col items-start gap-7">
            <span className="text-[13px] font-semibold uppercase tracking-[0.16em] text-primary">
              Private beta
            </span>
            <h1 className="font-serif text-[2.75rem] font-medium leading-[1.05] tracking-[-0.02em] text-foreground sm:text-[4.25rem]">
              Indian markets, the calm way.
            </h1>
            <p className="max-w-[620px] text-xl leading-[1.6] text-muted-foreground">
              Four momentum-based model portfolios and a daily insight engine —
              grounded in live market data, not noise. Built on our own
              portfolios, published for people who&apos;d rather follow what&apos;s
              actually leading than chase what&apos;s in the news.
            </p>
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                href="/sign-up"
                className="rounded-lg bg-primary px-6 py-3 text-base font-semibold text-primary-foreground transition-opacity hover:opacity-90"
              >
                Get beta access
              </Link>
              <Link
                href="/library"
                className="rounded-lg border border-border px-6 py-3 text-base font-semibold text-foreground transition-colors hover:border-primary/40"
              >
                Read the library
              </Link>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="border-t border-border px-6 py-20 sm:px-12 sm:py-28">
          <div className="mx-auto grid max-w-[1080px] gap-12 sm:grid-cols-3">
            {FEATURES.map((feature) => (
              <div key={feature.title} className="flex flex-col gap-3">
                <h2 className="font-serif text-2xl font-medium leading-[1.2] text-foreground">
                  {feature.title}
                </h2>
                <p className="text-[16px] leading-[1.6] text-muted-foreground">
                  {feature.body}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Portfolios */}
        <section className="border-t border-border px-6 py-20 sm:px-12 sm:py-28">
          <div className="mx-auto flex max-w-[1080px] flex-col gap-10">
            <div className="flex flex-col gap-4">
              <span className="text-[13px] font-semibold uppercase tracking-[0.16em] text-primary">
                The portfolios
              </span>
              <h2 className="max-w-[560px] font-serif text-[2.25rem] font-medium leading-[1.1] tracking-[-0.01em] text-foreground sm:text-[2.75rem]">
                Four ways to follow momentum.
              </h2>
              <p className="max-w-[560px] text-lg leading-[1.6] text-muted-foreground">
                Each portfolio is a rules-based momentum strategy on Indian
                equities, rebalanced on a schedule. Model portfolios for
                research and education — not personalised advice.
              </p>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              {portfolios.map((universe) => (
                <PortfolioCard key={universe.id} universe={universe} />
              ))}
            </div>
          </div>
        </section>

        {/* CTA band */}
        <section className="px-6 py-20 sm:px-12 sm:py-24">
          <div className="mx-auto flex max-w-[1080px] flex-col items-start gap-6 rounded-2xl bg-primary px-8 py-14 sm:px-14">
            <h2 className="max-w-[620px] font-serif text-[2rem] font-medium leading-[1.15] text-primary-foreground sm:text-[2.5rem]">
              Marketworks is in private beta.
            </h2>
            <p className="max-w-[560px] text-lg leading-[1.6] text-primary-foreground/85">
              Join the waitlist for access to the model portfolios and the daily
              insight engine. Free during beta.
            </p>
            <Link
              href="/sign-up"
              className="rounded-lg bg-background px-6 py-3 text-base font-semibold text-primary transition-opacity hover:opacity-90"
            >
              Get beta access
            </Link>
          </div>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}
