import Link from "next/link";
import Image from "next/image";
import { auth } from "@clerk/nextjs/server";

import { UNIVERSES } from "@/lib/universes";
import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { MarketingCard } from "@/components/marketing/marketing-card";
import { FeatureCard } from "@/components/marketing/feature-card";
import { SectionPanel } from "@/components/marketing/section-panel";
import { Reveal } from "@/components/marketing/reveal";

export const metadata = {
  title: "Marketworks — Indian markets, the calm way",
  description:
    "Three ready-made momentum portfolios and a daily market read for Indian " +
    "stocks, built on years of quantitative research. Process over " +
    "prediction. Currently in private beta.",
};

/* Loop 6 (PREFERENCES.md): iterative mode. KEEP the loop-4 gradient hero,
 * the drench CTA band, and the flat footer; the middle sections return to
 * the production design system (layered SectionPanels + illustrated cards —
 * the hierarchy the founder prefers). Snap scrolling removed. Changes are
 * now deliberately scoped section by section. */

const STEPS = [
  {
    title: "We rank the market",
    body: "Every week our system scores stocks by momentum: the simple idea that names already trending up tend to keep leading for a while.",
    image: {
      src: "/illustrations/fin-rank.webp",
      alt: "Hot-air balloons rising to different heights over misty hills; the ones with the most lift rise to the top",
    },
  },
  {
    title: "We build the portfolios",
    body: "The strongest names go into ready-made lists you can follow. When the leaders change, the list updates. No guessing, no headlines.",
    image: {
      src: "/illustrations/fin-build.webp",
      alt: "Hands picking only the ripest fruit from a branch into a basket, selecting the strongest names",
    },
  },
  {
    title: "You follow along",
    body: "See exactly what each portfolio holds, what changed at the last rebalance, and why, all in plain language.",
    image: {
      src: "/illustrations/fin-follow.webp",
      alt: "A figure walking a lantern-lit path over misty hills, a clear route to follow",
    },
  },
];

// Accent rotation for sibling portfolio cards (DESIGN.md §2.6) — static
// class strings so Tailwind sees them at build time.
const CARD_ACCENTS = [
  "border-acc1-line bg-acc1 text-acc1-fg",
  "border-acc2-line bg-acc2 text-acc2-fg",
  "border-acc4-line bg-acc4 text-acc4-fg",
  "border-acc5-line bg-acc5 text-acc5-fg",
] as const;

export default async function LandingPage() {
  const portfolios = Object.values(UNIVERSES).filter((u) => u.clientVisible);
  // Signed-in visitors already have access, so send them straight to the app.
  const { userId } = await auth();
  const betaHref = userId ? "/dashboard" : "/sign-up";
  const betaLabel = userId ? "View dashboard" : "Get beta access";

  return (
    <div className="mw-brand mw-mint2 mw-sans-headings relative min-h-screen overflow-hidden bg-surface-base">
      <FloatingNav />

      <main className="relative">
        {/* Hero — loop 8 experiment: grain + pastel gradient (Noto-banner
            reference), ink text on light ground. The dark mint sky variant
            stays in CSS (.mw-hero-sky-mint) for quick revert. */}
        <section className="mw-hero-drama relative flex min-h-[88vh] w-full flex-col justify-center overflow-hidden">
          <div className="relative mx-auto w-full max-w-[1240px] px-6 pb-28 pt-40 text-center lg:pb-24 lg:pt-28">
            <p className="font-mono text-sm text-white/70">private beta</p>
            <h1 className="mx-auto mt-6 max-w-[12ch] text-[3.4rem] font-medium leading-[1.02] tracking-[-0.025em] text-balance text-white sm:text-[6rem]">
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

        {/* PRODUCTION SYSTEM — welcome, inset mist panel */}
        <Reveal>
          <SectionPanel variant="mist" className="mt-10">
            <div className="max-w-[640px]">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                Welcome to the beta
              </span>
              <h2 className="mt-4 font-serif text-[2rem] font-medium leading-[1.15] tracking-[-0.01em] text-foreground sm:text-[2.5rem]">
                New here? Here&apos;s the whole idea in a minute.
              </h2>
              <p className="mt-5 text-lg leading-[1.65] text-muted-foreground">
                Thanks for being one of our first testers. Marketworks is a
                simpler way to invest in Indian stocks. Instead of picking names
                yourself or reacting to the news, you follow ready-made
                portfolios that are rebuilt on a fixed schedule (a
                &ldquo;rebalance&rdquo;) around the stocks that are currently
                leading the market.
              </p>
              <p className="mt-4 text-lg leading-[1.65] text-muted-foreground">
                It all runs on one idea called{" "}
                <span className="text-foreground">momentum</span>: stocks that
                have been rising tend to keep leading for a while. Our system
                measures this across the market every week, so the portfolios
                quietly stay with the leaders and step away as they fade.
              </p>
            </div>
          </SectionPanel>
        </Reveal>

        {/* PRODUCTION SYSTEM — how it works, image-led feature cards */}
        <section className="mx-auto max-w-[1140px] px-6 py-16 sm:py-24">
          <Reveal>
            <h2 className="max-w-[560px] font-serif text-[2rem] font-medium leading-[1.15] tracking-[-0.01em] text-foreground sm:text-[2.5rem]">
              How it works
            </h2>
          </Reveal>
          <div className="mt-10 grid gap-5 sm:grid-cols-3">
            {STEPS.map((step, i) => (
              <Reveal key={step.title} delayMs={i * 80}>
                <FeatureCard
                  eyebrow={`0${i + 1}`}
                  title={step.title}
                  body={step.body}
                  image={step.image}
                  tone={((i % 3) + 1) as 1 | 2 | 3}
                />
              </Reveal>
            ))}
          </div>
        </section>

        {/* PRODUCTION SYSTEM — research, inset deep panel */}
        <Reveal>
          <SectionPanel variant="deep">
            <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
              <div className="max-w-[600px]">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-secondary">
                  The research behind it
                </span>
                <h2 className="mt-4 font-serif text-[2rem] font-medium leading-[1.15] tracking-[-0.01em] text-surface-panel-deep-foreground sm:text-[2.5rem]">
                  Process over prediction.
                </h2>
                <p className="mt-5 text-lg leading-[1.65] text-surface-panel-deep-foreground/80">
                  Momentum is a{" "}
                  <span className="text-surface-panel-deep-foreground">
                    factor
                  </span>
                  : one of a small handful of forces that decades of research
                  have shown drive stock returns over time, alongside value and
                  quality.
                </p>
                <p className="mt-4 text-lg leading-[1.65] text-surface-panel-deep-foreground/80">
                  We&apos;ve spent years studying how it actually behaves in
                  Indian equities: validating it on periods our models had
                  never seen, and stress-testing it through crashes and
                  rallies. Only the rules that hold up on that unseen data earn
                  a place in a portfolio.
                </p>
                <Link
                  href="/library/welcome_to_marketworks_beta"
                  className="mt-6 inline-flex items-center gap-2 text-base font-semibold text-secondary transition-opacity hover:opacity-80"
                >
                  Read the full story
                  <span aria-hidden>→</span>
                </Link>
              </div>
              <div className="relative aspect-[4/3] w-full overflow-hidden rounded-2xl">
                <Image
                  src="/illustrations/fin-research.webp"
                  alt="A magnifying glass over a tree stump's growth rings, reading decades of market history"
                  fill
                  sizes="(max-width: 1024px) 100vw, 40vw"
                  className="object-cover"
                />
              </div>
            </div>
          </SectionPanel>
        </Reveal>

        {/* PRODUCTION SYSTEM — portfolios, 2-col intro + cards */}
        <section className="mx-auto max-w-[1140px] px-6 py-16 sm:py-24">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <Reveal>
              <div className="max-w-[560px]">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                  The portfolios
                </span>
                <h2 className="mt-4 font-serif text-[2.25rem] font-medium leading-[1.1] tracking-[-0.01em] text-foreground sm:text-[2.75rem]">
                  Three ways to follow momentum.
                </h2>
                <p className="mt-4 text-lg leading-[1.6] text-muted-foreground">
                  Each one is a rules-based list of Indian stocks, rebuilt on a
                  schedule so it stays with the current leaders. These are model
                  portfolios for research and education, not personalised
                  advice.
                </p>
              </div>
            </Reveal>
            <Reveal delayMs={80}>
              <div className="relative aspect-[4/3] w-full overflow-hidden rounded-card shadow-card">
                <Image
                  src="/illustrations/fin-portfolios.webp"
                  alt="Three potted plants of different character on a windowsill, three ways to follow momentum"
                  fill
                  sizes="(max-width: 1024px) 100vw, 48vw"
                  className="object-cover"
                />
              </div>
            </Reveal>
          </div>
          <div className="mt-12 grid gap-5 sm:grid-cols-2">
            {portfolios.map((universe, i) => (
              <Reveal key={universe.id} delayMs={(i % 2) * 80}>
                <MarketingCard className="h-full">
                  <div className="flex items-center justify-between gap-3">
                    <span
                      className={`rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${CARD_ACCENTS[i % CARD_ACCENTS.length]}`}
                    >
                      {universe.riskProfile}
                    </span>
                    <span className="font-mono text-sm text-muted-foreground">
                      {universe.stocks} stocks
                    </span>
                  </div>
                  <h3 className="mt-3 font-serif text-2xl font-medium leading-[1.2] text-foreground">
                    {universe.name}
                  </h3>
                  <p className="mt-2 text-[15px] leading-[1.55] text-muted-foreground">
                    {universe.description}
                  </p>
                  <Link
                    href="/portfolios"
                    className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
                  >
                    View portfolio <span aria-hidden>↗</span>
                  </Link>
                </MarketingCard>
              </Reveal>
            ))}
          </div>
        </section>

        {/* KEEP — the drench CTA band */}
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

        {/* KEEP — flat footer band */}
        <FooterPanel flat />
      </main>
    </div>
  );
}
