import Link from "next/link";
import { auth } from "@clerk/nextjs/server";
import { Eye, ListChecks, TrendingUp } from "lucide-react";

import { UNIVERSES } from "@/lib/universes";
import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { HeroFlow } from "@/components/marketing/hero-flow";
import { ResearchLens } from "@/components/marketing/research-lens";
import { SmoothScroll } from "@/components/marketing/smooth-scroll";
import {
  FactTile,
  SelectorPanel,
} from "@/components/marketing/selector-panel";
import {
  FeatureTile,
  GhostRows,
  GrainCard,
  GuideCard,
  SectionHeader,
  StackCard,
} from "@/components/marketing/study-cards";

export const metadata = {
  title: "Marketworks — Indian markets, the calm way",
  description:
    "Three ready-made momentum portfolios and a daily market read for Indian " +
    "stocks, built on years of quantitative research. Process over " +
    "prediction. Currently in private beta.",
};

/* Loop 17 (PREFERENCES.md): the homepage mid-page composed from the primitive
 * library, following the gallery recipe the founder named as the target —
 * one centered column, mono index captions (a deliberate brand system, not
 * scaffolding), varied card families chosen per content, generous air.
 * Hero (drama sky + tuned grain), drench CTA, and flat footer unchanged.
 * Ocean is the study's base palette. */

const STEPS = [
  {
    title: "We rank the market",
    body: "Every week our system scores stocks by momentum: the simple idea that names already trending up tend to keep leading for a while.",
    Icon: TrendingUp,
  },
  {
    title: "We build the portfolios",
    body: "The strongest names go into ready-made lists you can follow. When the leaders change, the list updates. No guessing, no headlines.",
    Icon: ListChecks,
  },
  {
    title: "You follow along",
    body: "See exactly what each portfolio holds, what changed at the last rebalance, and why, all in plain language.",
    Icon: Eye,
  },
];

/* Clay eyebrow treatment (CLAY_STUDY.md §1): small + semibold + uppercase +
 * wide tracking — the inverse of the huge/tight display type — and colored
 * in the section's accent hue so the vibrance arrives through elements on
 * the near-white ground. */
function SectionIndex({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <p
      className={`mb-6 font-mono text-[11px] font-semibold uppercase tracking-[0.16em] ${className ?? "text-muted-foreground"}`}
    >
      {children}
    </p>
  );
}

export default async function LandingPage() {
  const portfolios = Object.values(UNIVERSES).filter((u) => u.clientVisible);
  // Signed-in visitors already have access, so send them straight to the app.
  const { userId } = await auth();
  const betaHref = userId ? "/dashboard" : "/sign-up";
  const betaLabel = userId ? "View dashboard" : "Get beta access";

  return (
    <div className="mw-brand mw-serif-headings relative min-h-screen bg-surface-base">
      <SmoothScroll />
      <FloatingNav />

      <main className="relative">
        {/* Hero — dramatic palette sky with the tuned grain (unchanged) */}
        <section className="mw-hero-drama relative flex min-h-[88vh] w-full flex-col justify-center overflow-hidden">
          <div className="relative mx-auto w-full max-w-[1240px] px-6 pb-28 pt-40 text-center lg:pb-24 lg:pt-28">
            <p className="font-mono text-sm text-white/70">private beta</p>
            <h1 className="mx-auto mt-6 max-w-[12ch] text-[3.4rem] font-medium leading-[1.04] text-balance text-white sm:text-[6rem]">
              Indian markets, the calm way.
            </h1>
            <p className="mx-auto mt-7 max-w-[38em] text-lg leading-[1.6] text-white/85 sm:text-xl">
              Marketworks helps you follow the strongest stocks in the Indian
              market without watching it all day. You get three ready-made
              portfolios and a daily market read, built on live data instead of
              news and noise.
            </p>
            <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
              <Link
                href={betaHref}
                className="rounded-full bg-white px-6 py-3 text-base font-semibold text-primary transition-transform duration-150 hover:-translate-y-px"
              >
                {betaLabel}
              </Link>
              <Link
                href="/library"
                className="rounded-full border border-white/50 px-6 py-3 text-base font-semibold text-white transition-colors duration-150 hover:border-white"
              >
                Read the library
              </Link>
            </div>
          </div>
        </section>

        {/* Mid-page: the gallery recipe — centered column, indexed sections.
            The dot field sits on the full-bleed layer behind the column:
            visible at the page edges, dissolved under the content. */}
        <div className="relative">
          <div aria-hidden className="mw-dots-edge absolute inset-0" />
          <div className="relative mx-auto max-w-[1140px] px-6">
          {/* 01 — the idea: stack card with the flow-field motion */}
          <section className="pt-20 sm:pt-24">
            <SectionIndex className="text-acc1-fg">01 · the idea</SectionIndex>
            <StackCard
              label="Welcome to the beta"
              media={
                <div className="relative h-full min-h-[260px] w-full overflow-hidden rounded-[20px] bg-card">
                  <div aria-hidden className="mw-grid-fade absolute inset-0" />
                  <HeroFlow className="absolute inset-0" />
                </div>
              }
            >
              <h2 className="text-2xl font-semibold leading-[1.15] tracking-[-0.01em] sm:text-3xl">
                <span className="text-foreground">
                  New here? Here&apos;s the whole idea
                </span>{" "}
                <span className="text-acc1-fg">in a minute</span>
              </h2>
              <p className="mt-4 text-[15px] leading-[1.65] text-muted-foreground">
                Thanks for being one of our first testers. Marketworks is a
                simpler way to invest in Indian stocks. Instead of picking
                names yourself or reacting to the news, you follow ready-made
                portfolios that are rebuilt on a fixed schedule (a
                &ldquo;rebalance&rdquo;) around the stocks that are currently
                leading the market.
              </p>
              <p className="mt-3 text-[15px] leading-[1.65] text-muted-foreground">
                It all runs on one idea called{" "}
                <span className="font-semibold text-foreground">momentum</span>
                : stocks that have been rising tend to keep leading for a
                while. Our system measures this every week, so the portfolios
                quietly stay with the leaders and step away as they fade.
              </p>
            </StackCard>
          </section>

          {/* 02 — how it works: centered opener + soft tiles */}
          <section className="pt-20 sm:pt-28">
            <SectionIndex className="text-acc3-fg">02 · how it works</SectionIndex>
            {/* The primitives-gallery 04 recipe verbatim: soft card
                container, centered opener with the pill CTA, neutral
                tiles (clay.com end-to-end reference). */}
            <div className="rounded-[24px] border border-border/60 bg-card px-6 py-14 sm:px-10">
              <SectionHeader
                title="Momentum, done properly"
                sub="The system scores the whole market every week and keeps the portfolios with the leaders. No headlines, no hunches, no manual stock-picking."
                cta={{ href: betaHref, label: betaLabel }}
              />
              <div className="mt-12 grid gap-5 sm:grid-cols-3">
                {STEPS.map((step) => (
                  <FeatureTile
                    key={step.title}
                    icon={<step.Icon size={26} strokeWidth={1.75} aria-hidden />}
                    title={step.title}
                  >
                    {step.body}
                  </FeatureTile>
                ))}
              </div>
            </div>
          </section>

          {/* 03 — the research: grain card carries the process story */}
          <section className="pt-20 sm:pt-28">
            <SectionIndex className="text-acc2-fg">03 · the research</SectionIndex>
            <GrainCard visual={<ResearchLens />}>
              <h2 className="text-2xl font-semibold tracking-[-0.01em] text-foreground sm:text-3xl">
                Process over prediction
              </h2>
              <p className="mt-4 text-[15px] leading-[1.65] text-foreground/75">
                Momentum is a factor: one of a small handful of forces that
                decades of research have shown drive stock returns over time,
                alongside value and quality.
              </p>
              <p className="mt-3 text-[15px] leading-[1.65] text-foreground/75">
                We&apos;ve spent years studying how it behaves in Indian
                equities: validating it on periods our models had never seen,
                and stress-testing it through crashes and rallies. Only the
                rules that hold up on that unseen data earn a place in a
                portfolio.
              </p>
              <Link
                href="/library/welcome_to_marketworks_beta"
                className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary"
              >
                Read the full story <span aria-hidden>→</span>
              </Link>
            </GrainCard>
          </section>

          {/* 04 — the portfolios: interactive selector on real data */}
          <section className="pt-20 sm:pt-28">
            <SectionIndex className="text-acc4-fg">04 · the portfolios</SectionIndex>
            <SectionHeader
              title="Three ways to follow momentum"
              sub="Each one is a rules-based list of Indian stocks, rebuilt on a schedule so it stays with the current leaders."
            />
            <div className="mt-12">
              <SelectorPanel
                lead="Pick a portfolio to see what it follows and who it suits"
                footnote="Model portfolios for research and education, not personalised advice. Markets carry risk."
                items={portfolios.map((u) => ({
                  key: u.id,
                  label: u.name,
                  detail: (
                    <div>
                      <p className="font-mono text-xs uppercase tracking-[0.14em] text-acc1-fg">
                        Risk profile
                      </p>
                      <p className="mt-2 text-lg leading-[1.5] text-foreground">
                        {u.riskProfile}
                      </p>
                      <div className="mt-6 grid gap-4 sm:grid-cols-2">
                        <FactTile
                          label="Holdings"
                          value={`${u.stocks} stocks`}
                          note={u.description}
                        />
                        <FactTile
                          label="Rebuilt"
                          value="On schedule"
                          note="Rebalanced on a fixed cadence around the current market leaders."
                        />
                      </div>
                      <Link
                        href="/portfolios"
                        className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary"
                      >
                        View portfolio <span aria-hidden>↗</span>
                      </Link>
                    </div>
                  ),
                }))}
              />
            </div>
          </section>

          {/* 05 — from the library: framed guide cards */}
          <section className="pb-24 pt-20 sm:pt-28">
            <SectionIndex className="text-acc5-fg">05 · from the library</SectionIndex>
            <div className="grid gap-8 sm:grid-cols-2">
              <GuideCard
                href="/library/welcome_to_marketworks_beta"
                frameClassName="bg-acc1-line"
                tag="guide"
                tagClassName="bg-acc1 text-acc1-fg"
                title="What Marketworks is, and how to use it"
                meta={
                  <>
                    <span className="rounded-full border border-border px-3 py-1 text-xs font-semibold text-foreground">
                      Complete guide
                    </span>
                    <span>
                      /library <span aria-hidden>↗</span>
                    </span>
                  </>
                }
                media={<GhostRows rows={4} />}
              >
                Welcome to the beta: how the portfolios, the weekly rebalance,
                and the daily market read fit together.
              </GuideCard>
              <GuideCard
                href="/library"
                frameClassName="bg-acc2-line"
                tag="weekly roundup"
                tagClassName="bg-acc2 text-acc2-fg"
                title="A weak rupee is a slow tax on everything India imports"
                meta={
                  <>
                    <span className="rounded-full border border-border px-3 py-1 text-xs font-semibold text-foreground">
                      Weekly read
                    </span>
                    <span>
                      /library <span aria-hidden>↗</span>
                    </span>
                  </>
                }
                media={<GhostRows rows={4} />}
              >
                The headline this week was not the rupee, but the rupee is
                quietly making everything imported a little more expensive.
              </GuideCard>
            </div>
          </section>
          </div>
        </div>

        {/* Drench CTA band (unchanged keeper) */}
        <section className="relative w-full overflow-hidden bg-primary">
          <div
            aria-hidden
            className="mw-grid-inverse absolute inset-0 [mask-image:linear-gradient(to_left,#000_15%,transparent_62%)]"
          />
          <div className="relative mx-auto w-full max-w-[1240px] px-6 py-24 sm:py-28">
            <h2 className="max-w-[640px] text-[2rem] font-semibold leading-[1.1] tracking-[-0.02em] text-balance text-primary-foreground sm:text-[3rem]">
              Marketworks is in private beta.
            </h2>
            <p className="mt-4 max-w-[560px] text-lg leading-[1.6] text-primary-foreground/85">
              Sign up to follow the three portfolios and the daily market read.
              Free while we&apos;re in beta.
            </p>
            <Link
              href={betaHref}
              className="mt-8 inline-block rounded-full bg-white px-6 py-3 text-base font-semibold text-primary transition-transform duration-150 hover:-translate-y-px"
            >
              Get beta access
            </Link>
          </div>
        </section>

        <FooterPanel flat />
      </main>
    </div>
  );
}
