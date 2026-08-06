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

/* Variant C (PREFERENCES.md loop 4): full-bleed BANDED sections on a white
 * ground — no carded overlays. Atmospheric gradient hero (R4/P13), grid and
 * dot textures at band scale, and the Phantom takeover scroll (R3/P12): on
 * lg screens every band is sticky at top-0 and the next band slides over the
 * held one; mobile keeps normal flow. Experiment build — not final. */

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

const RISK_ACCENTS: Record<keyof typeof PROFILE_ICONS, string> = {
  defensive: "text-acc6-fg",
  growth: "text-acc2-fg",
  quality: "text-acc1-fg",
};

/* The takeover band: full-bleed, opaque, sticky on desktop so the next band
 * slides over it (P12). Content is height-capped to one viewport on lg. */
function Band({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`relative w-full lg:sticky lg:top-0 lg:flex lg:min-h-screen lg:flex-col lg:justify-center ${className ?? ""}`}
    >
      {children}
    </section>
  );
}

const bandHeading =
  "text-[1.9rem] font-semibold leading-[1.08] tracking-[-0.02em] sm:text-[2.6rem]";

function ValidationVisual({ onDark = false }: { onDark?: boolean }) {
  return (
    <svg viewBox="0 0 400 220" className="h-full w-full" aria-hidden>
      <rect
        x="236"
        y="12"
        width="152"
        height="196"
        rx="4"
        fill={onDark ? "#FFFFFF" : undefined}
        className={onDark ? undefined : "fill-acc1"}
        opacity={onDark ? 0.08 : 0.55}
      />
      <line
        x1="236"
        y1="12"
        x2="236"
        y2="208"
        stroke={onDark ? "#9CC3FF" : undefined}
        className={onDark ? undefined : "stroke-primary"}
        strokeWidth="1"
        strokeDasharray="3 4"
      />
      <path
        d="M12 168 C 48 150, 70 156, 96 138 S 150 118, 178 108 S 226 96, 252 78 S 320 60, 388 34"
        fill="none"
        stroke={onDark ? "#9CC3FF" : undefined}
        className={onDark ? undefined : "stroke-primary"}
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
    <div className="mw-brand mw-horizon relative min-h-screen bg-white">
      <FloatingNav />

      <main className="relative">
        {/* Band 1 — atmospheric gradient hero (R4/P13): giant tight sans in
            white on the Horizon sky; dot texture whispers in the dark zone */}
        <Band className="mw-hero-sky overflow-hidden">
          <div
            aria-hidden
            className="mw-dots-light absolute inset-x-0 top-0 h-1/2 opacity-40 [mask-image:linear-gradient(to_bottom,#000,transparent)]"
          />
          <div className="relative mx-auto w-full max-w-[1240px] px-6 pb-24 pt-40 text-center lg:pb-16 lg:pt-24">
            <p className="font-mono text-sm text-white/70">private beta</p>
            <h1 className="mx-auto mt-6 max-w-[12ch] text-[3.4rem] font-medium leading-[1.02] tracking-[-0.035em] text-balance text-white sm:text-[6rem]">
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
                className="rounded-full bg-white px-6 py-3 text-base font-semibold text-[#0A47D8] transition-transform duration-150 hover:-translate-y-px"
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
        </Band>

        {/* Band 2 — welcome, white band; the quant candles live here now,
            drawn on the white ground under the copy */}
        <Band className="bg-white">
          <div className="mx-auto w-full max-w-[1240px] px-6 py-20 lg:py-0">
            <div className="grid items-center gap-12 lg:grid-cols-[1fr_0.85fr]">
              <div className="max-w-[640px]">
                <h2 className={`${bandHeading} text-foreground`}>
                  New here? Here&apos;s the whole idea in a minute.
                </h2>
                <p className="mt-5 text-lg leading-[1.65] text-muted-foreground">
                  Thanks for being one of our first testers. Marketworks is a
                  simpler way to invest in Indian stocks. Instead of picking
                  names yourself or reacting to the news, you follow ready-made
                  portfolios that are rebuilt on a fixed schedule (a
                  &ldquo;rebalance&rdquo;) around the stocks that are currently
                  leading the market.
                </p>
                <p className="mt-4 text-lg leading-[1.65] text-muted-foreground">
                  It all runs on one idea called{" "}
                  <span className="text-foreground">momentum</span>: stocks
                  that have been rising tend to keep leading for a while. Our
                  system measures this across the market every week, so the
                  portfolios quietly stay with the leaders and step away as
                  they fade.
                </p>
              </div>
              <div className="relative h-[260px] lg:h-[340px]">
                <div
                  aria-hidden
                  className="mw-grid absolute inset-0 opacity-70 [mask-image:radial-gradient(ellipse_80%_85%_at_50%_50%,#000_35%,transparent_85%)]"
                />
                <HeroQuant className="absolute inset-0" />
              </div>
            </div>
          </div>
        </Band>

        {/* Band 3 — how it works, tinted band with the editorial grid at
            section scale; flat columns, no cards */}
        <Band className="bg-acc1">
          <div aria-hidden className="mw-grid absolute inset-0 opacity-50" />
          <div className="relative mx-auto w-full max-w-[1240px] px-6 py-20 lg:py-0">
            <h2 className={`${bandHeading} text-foreground`}>How it works</h2>
            <div className="mt-12 grid gap-10 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-[color:var(--acc1-line)]/25">
              {STEPS.map((step, i) => (
                <div key={step.title} className="sm:px-8 sm:first:pl-0 sm:last:pr-0">
                  <div className="flex items-center justify-between">
                    <step.Icon
                      size={22}
                      strokeWidth={1.75}
                      aria-hidden
                      className="text-primary"
                    />
                    <span className="font-mono text-sm text-primary">
                      0{i + 1}
                    </span>
                  </div>
                  <h3 className="mt-5 text-xl font-semibold leading-[1.2] tracking-[-0.01em] text-foreground">
                    {step.title}
                  </h3>
                  <p className="mt-2.5 text-[15px] leading-[1.6] text-muted-foreground">
                    {step.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </Band>

        {/* Band 4 — research, deep navy band with the loved dot texture */}
        <Band className="bg-[#0A1B3D] text-white">
          <div aria-hidden className="mw-dots-light absolute inset-0 opacity-30" />
          <div className="relative mx-auto w-full max-w-[1240px] px-6 py-20 lg:py-0">
            <div className="grid items-center gap-12 lg:grid-cols-[1fr_0.8fr]">
              <div className="max-w-[640px]">
                <h2 className={bandHeading}>Process over prediction.</h2>
                <p className="mt-5 text-lg leading-[1.65] text-white/80">
                  Momentum is a <span className="text-white">factor</span>: one
                  of a small handful of forces that decades of research have
                  shown drive stock returns over time, alongside value and
                  quality.
                </p>
                <p className="mt-4 text-lg leading-[1.65] text-white/80">
                  We&apos;ve spent years studying how it actually behaves in
                  Indian equities: validating it on periods our models had
                  never seen, and stress-testing it through crashes and
                  rallies. Only the rules that hold up on that unseen data earn
                  a place in a portfolio.
                </p>
                <Link
                  href="/library/welcome_to_marketworks_beta"
                  className="group mt-6 inline-flex items-center gap-2 text-base font-semibold text-[#9CC3FF]"
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
              <figure>
                <div className="relative aspect-[16/9]">
                  <ValidationVisual onDark />
                </div>
                <figcaption className="mt-3 font-mono text-xs text-white/55">
                  rules tested on periods the models never saw
                </figcaption>
              </figure>
            </div>
          </div>
        </Band>

        {/* Band 5 — portfolios, white band, flat divided columns */}
        <Band className="bg-white">
          <div className="mx-auto w-full max-w-[1240px] px-6 py-20 lg:py-0">
            <div className="max-w-[640px]">
              <h2 className={`${bandHeading} text-foreground`}>
                Three ways to follow momentum.
              </h2>
              <p className="mt-4 text-lg leading-[1.6] text-muted-foreground">
                Each one is a rules-based list of Indian stocks, rebuilt on a
                schedule so it stays with the current leaders. These are model
                portfolios for research and education, not personalised advice.
              </p>
            </div>
            <div className="mt-12 grid gap-10 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-border">
              {portfolios.map((universe) => {
                const kind = riskKind(universe.riskProfile);
                /* eslint-disable security/detect-object-injection -- kind is
                 * the typed literal return of riskKind() against
                 * module-level const maps */
                const Icon = PROFILE_ICONS[kind];
                const accent = RISK_ACCENTS[kind];
                /* eslint-enable security/detect-object-injection */
                return (
                  <Link
                    key={universe.id}
                    href="/portfolios"
                    className="group flex h-full flex-col sm:px-8 sm:first:pl-0 sm:last:pr-0"
                  >
                    <div className="flex min-h-10 items-baseline justify-between gap-3">
                      <span
                        className={`font-mono text-sm lowercase ${accent}`}
                      >
                        {universe.riskProfile}
                      </span>
                      <span className="font-mono text-sm text-muted-foreground">
                        {universe.stocks} stocks
                      </span>
                    </div>
                    <h3 className="mt-3 flex items-center gap-2.5 text-xl font-semibold leading-[1.2] tracking-[-0.01em] text-foreground">
                      <Icon
                        size={18}
                        strokeWidth={1.75}
                        aria-hidden
                        className={accent}
                      />
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
                );
              })}
            </div>
          </div>
        </Band>

        {/* Band 6 — the drench CTA, unchanged model (the confirmed keeper) */}
        <Band className="overflow-hidden bg-primary">
          <div
            aria-hidden
            className="mw-grid-inverse absolute inset-0 [mask-image:linear-gradient(to_left,#000_15%,transparent_62%)]"
          />
          <div className="relative mx-auto w-full max-w-[1240px] px-6 py-24 lg:py-0">
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
        </Band>

        <div className="relative">
          <FooterPanel flat />
        </div>
      </main>
    </div>
  );
}
