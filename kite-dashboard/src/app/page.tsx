import Link from "next/link";
import Image from "next/image";

import { UNIVERSES } from "@/lib/universes";
import { FloatingNav } from "@/components/marketing/floating-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingBackground } from "@/components/marketing/marketing-background";
import { MarketingCard } from "@/components/marketing/marketing-card";
import { FeatureCard } from "@/components/marketing/feature-card";
import { SectionPanel } from "@/components/marketing/section-panel";
import { Reveal } from "@/components/marketing/reveal";

export const metadata = {
  title: "Marketworks — Indian markets, the calm way",
  description:
    "Three ready-made momentum portfolios and a daily market read for Indian " +
    "stocks — built on years of quantitative research, not hunches. Process " +
    "over prediction. Currently in private beta.",
};

const STEPS = [
  {
    title: "We rank the market",
    body: "Every week our system scores stocks by momentum — the simple idea that names already trending up tend to keep leading for a while.",
    image: {
      src: "/illustrations/fin-rank.webp",
      alt: "Hot-air balloons rising to different heights over misty hills — the ones with the most lift rise to the top",
    },
  },
  {
    title: "We build the portfolios",
    body: "The strongest names go into ready-made lists you can follow. When the leaders change, the list updates — no guessing, no headlines.",
    image: {
      src: "/illustrations/fin-build.webp",
      alt: "Hands picking only the ripest fruit from a branch into a basket — selecting the strongest names",
    },
  },
  {
    title: "You follow along",
    body: "See exactly what each portfolio holds, what changed at the last rebalance, and why — all in plain language.",
    image: {
      src: "/illustrations/fin-follow.webp",
      alt: "A figure walking a lantern-lit path over misty hills — a clear route to follow",
    },
  },
];

// The hero illustration floats on the base with soft-faded edges (no card
// frame), so its grain melts into the near-white surface.
const HERO_FADE =
  "radial-gradient(ellipse 80% 80% at 50% 46%, #000 58%, transparent 100%)";

function HeroGraphic() {
  return (
    <div className="relative aspect-square w-full">
      <Image
        src="/illustrations/fin-hero.webp"
        alt="A lone figure at a window quietly watching a valley of misty hills at dawn"
        fill
        sizes="(max-width: 900px) 100vw, 48vw"
        className="object-cover"
        style={{ maskImage: HERO_FADE, WebkitMaskImage: HERO_FADE }}
        priority
      />
    </div>
  );
}

export default function LandingPage() {
  const portfolios = Object.values(UNIVERSES).filter((u) => u.clientVisible);

  return (
    <div className="mw-brand relative min-h-screen overflow-hidden bg-surface-base">
      {/* Quant grid — contained to the hero zone; the rest of the base stays clean. */}
      <MarketingBackground
        texture="grid"
        className="absolute inset-x-0 top-0 h-[820px] [mask-image:radial-gradient(120%_80%_at_72%_6%,#000,transparent_78%)]"
      />

      <FloatingNav />

      <main className="relative">
        {/* Hero */}
        <section className="mx-auto max-w-[1140px] px-6 pb-16 pt-32 sm:pt-40">
          <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
            <Reveal>
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                Private beta
              </span>
              <h1 className="mt-5 font-serif text-[2.75rem] font-medium leading-[1.03] tracking-[-0.02em] text-balance text-foreground sm:text-[4.25rem]">
                Indian markets, the{" "}
                <span className="relative whitespace-nowrap text-primary">
                  calm
                  <svg
                    viewBox="0 0 200 12"
                    preserveAspectRatio="none"
                    aria-hidden
                    className="absolute -bottom-1 left-0 h-[0.2em] w-full overflow-visible"
                  >
                    <path
                      d="M3 8 C 55 3, 150 3, 197 7"
                      className="stroke-secondary"
                      strokeWidth="3"
                      strokeLinecap="round"
                      fill="none"
                    />
                  </svg>
                </span>{" "}
                way.
              </h1>
              <p className="mt-6 max-w-[34em] text-lg leading-[1.6] text-muted-foreground sm:text-xl">
                Marketworks helps you follow the strongest stocks in the Indian
                market — without watching it all day. You get three ready-made
                portfolios and a daily market read, built on live data instead of
                news and noise.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link
                  href="/sign-up"
                  className="rounded-full bg-primary px-6 py-3 text-base font-semibold text-primary-foreground transition-[transform,box-shadow] duration-200 ease-expo hover:-translate-y-px hover:shadow-md"
                >
                  Get beta access
                </Link>
                <Link
                  href="/library"
                  className="rounded-full border border-border px-6 py-3 text-base font-semibold text-foreground transition-colors hover:border-primary/40"
                >
                  Read the library
                </Link>
              </div>
            </Reveal>

            <Reveal delayMs={80}>
              <HeroGraphic />
            </Reveal>
          </div>
        </section>

        {/* Welcome — inset mist panel */}
        <Reveal>
          <SectionPanel variant="mist">
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
                yourself or reacting to the news, you follow ready-made portfolios
                that are rebuilt on a fixed schedule — a &ldquo;rebalance&rdquo; —
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
          </SectionPanel>
        </Reveal>

        {/* How it works — image-led feature cards float on the base */}
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
                />
              </Reveal>
            ))}
          </div>
        </section>

        {/* Research — inset deep panel (the dark contrast moment), 2-col with art */}
        <Reveal>
          <SectionPanel variant="deep">
            <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
              <div className="max-w-[600px]">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-secondary">
                  The research behind it
                </span>
                <h2 className="mt-4 font-serif text-[2rem] font-medium leading-[1.15] tracking-[-0.01em] text-primary-foreground sm:text-[2.5rem]">
                  Process over prediction.
                </h2>
                <p className="mt-5 text-lg leading-[1.65] text-primary-foreground/80">
                  Momentum isn&apos;t a hunch. It&apos;s a{" "}
                  <span className="text-primary-foreground">factor</span> — one of
                  a small handful of forces that decades of research have shown
                  drive stock returns over time, alongside things like value and
                  quality.
                </p>
                <p className="mt-4 text-lg leading-[1.65] text-primary-foreground/80">
                  We&apos;ve spent years studying how it actually behaves in
                  Indian equities: validating it on periods our models had never
                  seen, and stress-testing it through crashes and rallies. Only
                  the rules that hold up on that unseen data earn a place in a
                  portfolio.
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
                  alt="A magnifying glass over a tree stump's growth rings — reading decades of market history"
                  fill
                  sizes="(max-width: 1024px) 100vw, 40vw"
                  className="object-cover"
                />
              </div>
            </div>
          </SectionPanel>
        </Reveal>

        {/* Portfolios — 2-col intro + cards */}
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
                  portfolios for research and education, not personalised advice.
                </p>
              </div>
            </Reveal>
            <Reveal delayMs={80}>
              <div className="relative aspect-[4/3] w-full overflow-hidden rounded-card shadow-card">
                <Image
                  src="/illustrations/fin-portfolios.webp"
                  alt="Three potted plants of different character on a windowsill — three ways to follow momentum"
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
                    <span className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
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

        {/* CTA — inset lichen panel */}
        <Reveal>
          <SectionPanel variant="lichen">
            <div className="flex max-w-[640px] flex-col items-start gap-6">
              <h2 className="font-serif text-[2rem] font-medium leading-[1.15] text-primary-foreground sm:text-[2.5rem]">
                Marketworks is in private beta.
              </h2>
              <p className="text-lg leading-[1.6] text-primary-foreground/85">
                Sign up to follow the three portfolios and the daily market read.
                Free while we&apos;re in beta.
              </p>
              <Link
                href="/sign-up"
                className="rounded-full bg-surface-base px-6 py-3 text-base font-semibold text-primary transition-[transform,box-shadow] duration-200 ease-expo hover:-translate-y-px hover:shadow-md"
              >
                Get beta access
              </Link>
            </div>
          </SectionPanel>
        </Reveal>

        <div className="h-8" />
      </main>

      <MarketingFooter />
    </div>
  );
}
