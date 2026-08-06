import Link from "next/link";
import { auth } from "@clerk/nextjs/server";
import {
  Eye,
  ListChecks,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { UNIVERSES } from "@/lib/universes";
import { FloatingNav } from "@/components/marketing/floating-nav";
import { FooterPanel } from "@/components/marketing/footer-panel";
import { HeroQuant } from "@/components/marketing/hero-quant";

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

const PROFILE_ICONS = {
  defensive: ShieldCheck,
  growth: TrendingUp,
  quality: Sparkles,
} as const;

function riskKind(riskProfile: string): keyof typeof PROFILE_ICONS {
  const p = riskProfile.toLowerCase();
  if (p.includes("drawdown") || p.includes("defensive")) return "defensive";
  if (p.includes("growth")) return "growth";
  return "quality";
}

const sectionHeading =
  "text-[1.75rem] font-semibold leading-[1.1] tracking-[-0.02em] text-foreground sm:text-[2.25rem]";

// Polychrome with semantics (critique follow-up): color is mapped to what the
// portfolio IS, not to sibling order — defensive never wears the loss color.
const RISK_ACCENTS: Record<keyof typeof PROFILE_ICONS, string> = {
  defensive: "text-acc6-fg",
  growth: "text-acc2-fg",
  quality: "text-acc1-fg",
};

/* Abstract, deterministic quant illustrations for the middle sections.
 * Decorative only — no numbers, no fabricated performance data. */

function RankStripVisual() {
  const bars = [86, 64, 52, 38, 27];
  return (
    <svg viewBox="0 0 400 220" className="h-full w-full" aria-hidden>
      {bars.map((len, i) => (
        <g key={len} transform={`translate(40 ${34 + i * 38})`}>
          <rect
            x="0"
            y="0"
            width={len * 3.2}
            height="14"
            rx="2"
            className="fill-primary"
            opacity={0.92 - i * 0.17}
          />
          <rect
            x={len * 3.2 + 8}
            y="4"
            width="6"
            height="6"
            className={i === 0 ? "fill-secondary" : "fill-border"}
          />
        </g>
      ))}
    </svg>
  );
}

function ValidationVisual() {
  return (
    <svg viewBox="0 0 400 220" className="h-full w-full" aria-hidden>
      <rect x="236" y="12" width="152" height="196" rx="4" className="fill-acc1" opacity="0.55" />
      <line x1="236" y1="12" x2="236" y2="208" className="stroke-primary" strokeWidth="1" strokeDasharray="3 4" />
      <path
        d="M12 168 C 48 150, 70 156, 96 138 S 150 118, 178 108 S 226 96, 252 78 S 320 60, 388 34"
        fill="none"
        className="stroke-primary"
        strokeWidth="2.25"
        strokeLinecap="round"
      />
      {[
        [96, 138],
        [178, 108],
        [252, 78],
        [330, 52],
      ].map(([x, y]) => (
        <circle key={x} cx={x} cy={y} r="3.5" className="fill-secondary" />
      ))}
    </svg>
  );
}

export default async function LandingPage() {
  const portfolios = Object.values(UNIVERSES).filter((u) => u.clientVisible);
  // Signed-in visitors already have access, so send them straight to the app.
  const { userId } = await auth();
  const betaHref = userId ? "/dashboard" : "/sign-up";
  const betaLabel = userId ? "View dashboard" : "Get beta access";

  return (
    <div className="mw-brand mw-bright mw-horizon relative min-h-screen overflow-hidden bg-surface-base">
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

          {/* Motion as identity (P7/P11): dithered data field + breathing
              candlesticks on chart-paper — the quant texture, and mobile
              finally gets it too (shorter band, lighter density). */}
          <div className="relative mt-8 h-[200px] w-full sm:mt-10 sm:h-[38vh] sm:min-h-[280px]">
            <div
              aria-hidden
              className="mw-grid absolute inset-0 [mask-image:radial-gradient(ellipse_72%_88%_at_50%_50%,#000_30%,transparent_76%)]"
            />
            <HeroQuant className="absolute inset-0" />
          </div>
        </section>

        {/* Welcome — flat, hairline rule opens the section; ranking strip
            visual keeps the band from falling flat */}
        <section className="mx-auto max-w-[1140px] border-t border-border px-6 py-20 sm:py-24">
          <div className="grid gap-10 lg:grid-cols-[1fr_0.8fr] lg:items-center">
            <div className="max-w-[680px]">
              <h2 className={sectionHeading}>
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
            <figure className="hidden lg:block">
              <div className="relative aspect-[16/9] overflow-hidden rounded-lg border border-border bg-card">
                <div
                  aria-hidden
                  className="mw-grid absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_85%_85%_at_50%_50%,#000_40%,transparent_90%)]"
                />
                <RankStripVisual />
              </div>
              <figcaption className="mt-3 font-mono text-xs text-muted-foreground">
                nse 500 · scored weekly · leaders rise
              </figcaption>
            </figure>
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
                <div className="flex items-center justify-between">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border text-primary">
                    <step.Icon size={19} strokeWidth={1.75} aria-hidden />
                  </span>
                  <span className="font-mono text-sm text-primary">
                    0{i + 1}
                  </span>
                </div>
                <h3 className="mt-4 text-xl font-semibold leading-[1.2] tracking-[-0.01em] text-foreground">
                  {step.title}
                </h3>
                <p className="mt-2 text-[15px] leading-[1.55] text-muted-foreground">
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Research — validation visual answers "years of research" with a
            picture of the method (abstract, no fabricated numbers) */}
        <section className="mx-auto max-w-[1140px] border-t border-border px-6 py-20 sm:py-24">
          <div className="grid gap-10 lg:grid-cols-[1fr_0.8fr] lg:items-center">
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
          <figure className="hidden lg:block">
            <div className="relative aspect-[16/9] overflow-hidden rounded-lg border border-border bg-card">
              <div
                aria-hidden
                className="mw-grid absolute inset-0 opacity-60 [mask-image:radial-gradient(ellipse_85%_85%_at_50%_50%,#000_40%,transparent_90%)]"
              />
              <ValidationVisual />
            </div>
            <figcaption className="mt-3 font-mono text-xs text-muted-foreground">
              rules tested on periods the models never saw
            </figcaption>
          </figure>
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
                <div className="flex min-h-10 items-baseline justify-between gap-3">
                  <span
                    className={`font-mono text-sm lowercase ${RISK_ACCENTS[riskKind(universe.riskProfile)]}`}
                  >
                    {universe.riskProfile}
                  </span>
                  <span className="font-mono text-sm text-muted-foreground">
                    {universe.stocks} stocks
                  </span>
                </div>
                <h3 className="mt-3 flex items-center gap-2.5 text-xl font-semibold leading-[1.2] tracking-[-0.01em] text-foreground">
                  {(() => {
                    const Icon = PROFILE_ICONS[riskKind(universe.riskProfile)];
                    return (
                      <Icon
                        size={18}
                        strokeWidth={1.75}
                        aria-hidden
                        className={RISK_ACCENTS[riskKind(universe.riskProfile)]}
                      />
                    );
                  })()}
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
        <section className="relative overflow-hidden bg-primary">
          {/* Grid as field texture inside the drench: emerges on the right,
              masked away from the copy. */}
          <div
            aria-hidden
            className="mw-grid-inverse absolute inset-0 [mask-image:linear-gradient(to_left,#000_15%,transparent_62%)]"
          />
          <div className="relative mx-auto max-w-[1140px] px-6 py-24 sm:py-28">
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

        <FooterPanel flat />
      </main>
    </div>
  );
}
