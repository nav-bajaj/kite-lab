import Link from "next/link";
import { auth } from "@clerk/nextjs/server";

import { UNIVERSES } from "@/lib/universes";
import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { HeroFlow } from "@/components/marketing/hero-flow";

export const metadata = {
  title: "Marketworks — Indian markets, the calm way",
  description:
    "Three ready-made momentum portfolios and a daily market read for Indian " +
    "stocks, built on years of quantitative research. Process over " +
    "prediction. Currently in private beta.",
};

/* Study loop 1, Variant B (PREFERENCES.md R2 — base.org): radical reduction.
 * Flat near-white ground, hairline-bordered modules, sans display type, mono
 * metadata labels instead of tracked eyebrows, 150ms micro-transitions, one
 * full-bleed drench at the CTA. The bespoke HeroFlow canvas stays as the
 * motion-as-identity texture (P7). Shared marketing components are untouched;
 * this page carries its own flat markup while the direction is under study. */

const STEPS = [
  {
    title: "We rank the market",
    body: "Every week our system scores stocks by momentum: the simple idea that names already trending up tend to keep leading for a while.",
  },
  {
    title: "We build the portfolios",
    body: "The strongest names go into ready-made lists you can follow. When the leaders change, the list updates. No guessing, no headlines.",
  },
  {
    title: "You follow along",
    body: "See exactly what each portfolio holds, what changed at the last rebalance, and why, all in plain language.",
  },
];

const sectionHeading =
  "text-[1.75rem] font-semibold leading-[1.1] tracking-[-0.02em] text-foreground sm:text-[2.25rem]";

export default async function LandingPage() {
  const portfolios = Object.values(UNIVERSES).filter((u) => u.clientVisible);
  // Signed-in visitors already have access, so send them straight to the app.
  const { userId } = await auth();
  const betaHref = userId ? "/dashboard" : "/sign-up";
  const betaLabel = userId ? "View dashboard" : "Get beta access";

  return (
    <div className="mw-brand relative min-h-screen overflow-hidden bg-surface-base">
      <FloatingNav />

      <main className="relative z-10">
        {/* Hero — sans display, mono kicker, canvas band below (desktop) */}
        <section className="relative flex flex-col overflow-hidden pb-10 pt-32 sm:pt-40">
          <div className="mx-auto max-w-[880px] px-6 text-center">
            <p className="font-mono text-sm text-muted-foreground">
              private beta
            </p>
            <h1 className="mt-6 text-[3rem] font-semibold leading-[1.02] tracking-[-0.03em] text-balance text-foreground sm:text-[4.75rem]">
              Indian markets, the{" "}
              <span className="text-display-accent">calm</span> way.
            </h1>
            <p className="mx-auto mt-6 max-w-[40em] text-lg leading-[1.6] text-muted-foreground sm:text-xl">
              Marketworks helps you follow the strongest stocks in the Indian
              market without watching it all day. You get three ready-made
              portfolios and a daily market read, built on live data instead of
              news and noise.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <Link
                href={betaHref}
                className="rounded-full bg-primary px-6 py-3 text-base font-semibold text-primary-foreground transition-transform duration-150 hover:-translate-y-px"
              >
                {betaLabel}
              </Link>
              <Link
                href="/library"
                className="rounded-full border border-border px-6 py-3 text-base font-semibold text-foreground transition-colors duration-150 hover:border-primary"
              >
                Read the library
              </Link>
            </div>
          </div>

          {/* Motion as identity (P7): the live flow-field canvas is the one
              hero texture; the page around it stays still. */}
          <div className="relative mt-10 hidden h-[42vh] min-h-[300px] w-full md:block">
            <HeroFlow className="absolute inset-0" />
          </div>
        </section>

        {/* Welcome — flat, hairline rule opens the section */}
        <section className="mx-auto max-w-[1140px] border-t border-border px-6 py-20 sm:py-24">
          <div className="max-w-[680px]">
            <h2 className={sectionHeading}>
              New here? Here&apos;s the whole idea in a minute.
            </h2>
            <p className="mt-5 text-lg leading-[1.65] text-muted-foreground">
              Thanks for being one of our first testers. Marketworks is a
              simpler way to invest in Indian stocks. Instead of picking names
              yourself or reacting to the news, you follow ready-made portfolios
              that are rebuilt on a fixed schedule (a &ldquo;rebalance&rdquo;)
              around the stocks that are currently leading the market.
            </p>
            <p className="mt-4 text-lg leading-[1.65] text-muted-foreground">
              It all runs on one idea called{" "}
              <span className="text-foreground">momentum</span>: stocks that
              have been rising tend to keep leading for a while. Our system
              measures this across the market every week, so the portfolios
              quietly stay with the leaders and step away as they fade.
            </p>
          </div>
        </section>

        {/* How it works — flat bordered modules; the 3-step order is real,
            so the mono step numbers carry information */}
        <section className="mx-auto max-w-[1140px] border-t border-border px-6 py-20 sm:py-24">
          <h2 className={sectionHeading}>How it works</h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {STEPS.map((step, i) => (
              <div
                key={step.title}
                className="rounded-lg border border-border bg-card p-7 transition-colors duration-150 hover:border-primary"
              >
                <span className="font-mono text-sm text-muted-foreground">
                  0{i + 1}
                </span>
                <h3 className="mt-3 text-xl font-semibold leading-[1.2] tracking-[-0.01em] text-foreground">
                  {step.title}
                </h3>
                <p className="mt-2 text-[15px] leading-[1.55] text-muted-foreground">
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Research — flat text section, type does the talking */}
        <section className="mx-auto max-w-[1140px] border-t border-border px-6 py-20 sm:py-24">
          <div className="max-w-[680px]">
            <h2 className={sectionHeading}>Process over prediction.</h2>
            <p className="mt-5 text-lg leading-[1.65] text-muted-foreground">
              Momentum is a <span className="text-foreground">factor</span>:
              one of a small handful of forces that decades of research have
              shown drive stock returns over time, alongside value and quality.
            </p>
            <p className="mt-4 text-lg leading-[1.65] text-muted-foreground">
              We&apos;ve spent years studying how it actually behaves in Indian
              equities: validating it on periods our models had never seen, and
              stress-testing it through crashes and rallies. Only the rules
              that hold up on that unseen data earn a place in a portfolio.
            </p>
            <Link
              href="/library/welcome_to_marketworks_beta"
              className="group mt-6 inline-flex items-center gap-2 text-base font-semibold text-primary"
            >
              Read the full story
              <span
                aria-hidden
                className="transition-transform duration-150 group-hover:translate-x-0.5"
              >
                →
              </span>
            </Link>
          </div>
        </section>

        {/* Portfolios — flat bordered cards, mono metadata */}
        <section className="mx-auto max-w-[1140px] border-t border-border px-6 py-20 sm:py-24">
          <div className="max-w-[680px]">
            <h2 className={sectionHeading}>Three ways to follow momentum.</h2>
            <p className="mt-4 text-lg leading-[1.6] text-muted-foreground">
              Each one is a rules-based list of Indian stocks, rebuilt on a
              schedule so it stays with the current leaders. These are model
              portfolios for research and education, not personalised advice.
            </p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {portfolios.map((universe) => (
              <Link
                key={universe.id}
                href="/portfolios"
                className="group flex h-full flex-col rounded-lg border border-border bg-card p-7 transition-colors duration-150 hover:border-primary"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-sm lowercase text-muted-foreground">
                    {universe.riskProfile}
                  </span>
                  <span className="font-mono text-sm text-muted-foreground">
                    {universe.stocks} stocks
                  </span>
                </div>
                <h3 className="mt-3 text-xl font-semibold leading-[1.2] tracking-[-0.01em] text-foreground">
                  {universe.name}
                </h3>
                <p className="mt-2 text-[15px] leading-[1.55] text-muted-foreground">
                  {universe.description}
                </p>
                <span className="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm font-semibold text-primary">
                  View portfolio
                  <span
                    aria-hidden
                    className="transition-transform duration-150 group-hover:translate-x-0.5"
                  >
                    →
                  </span>
                </span>
              </Link>
            ))}
          </div>
        </section>

        {/* CTA — the one drench (P9): full-bleed primary, deliberately
            breaking the inset-panel rule for this variant */}
        <section className="bg-primary">
          <div className="mx-auto max-w-[1140px] px-6 py-24 sm:py-28">
            <h2 className="max-w-[640px] text-[2rem] font-semibold leading-[1.1] tracking-[-0.02em] text-balance text-primary-foreground sm:text-[3rem]">
              Marketworks is in private beta.
            </h2>
            <p className="mt-4 max-w-[560px] text-lg leading-[1.6] text-primary-foreground/85">
              Sign up to follow the three portfolios and the daily market read.
              Free while we&apos;re in beta.
            </p>
            <Link
              href={betaHref}
              className="mt-8 inline-block rounded-full bg-surface-base px-6 py-3 text-base font-semibold text-primary transition-transform duration-150 hover:-translate-y-px"
            >
              Get beta access
            </Link>
          </div>
        </section>

        <div className="relative z-10 pb-6">
          <FooterPanel />
        </div>
      </main>
    </div>
  );
}
