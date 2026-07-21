import Link from "next/link";
import { auth } from "@clerk/nextjs/server";

import { UNIVERSES } from "@/lib/universes";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { PortfolioCard } from "@/components/marketing/portfolio-card";

export const metadata = {
  title: "Marketworks — Indian markets, the calm way",
  description:
    "Three ready-made momentum portfolios and a daily market read for Indian " +
    "stocks — built on years of quantitative research, not hunches. Process " +
    "over prediction. Currently in private beta.",
};

// Three plain-language steps for a newcomer. Each answers "what actually
// happens" — no jargon that isn't explained in the same line.
const STEPS = [
  {
    title: "We rank the market",
    body: "Every week our system scores stocks by momentum — the simple idea that names already trending up tend to keep leading for a while.",
  },
  {
    title: "We build the portfolios",
    body: "The strongest names go into ready-made lists you can follow. When the leaders change, the list updates — no guessing, no headlines.",
  },
  {
    title: "You follow along",
    body: "See exactly what each portfolio holds, what changed at the last rebalance, and why — all in plain language.",
  },
];

export default async function LandingPage() {
  const portfolios = Object.values(UNIVERSES).filter((u) => u.clientVisible);
  // Signed-in visitors already have access, so send them straight to the app.
  const { userId } = await auth();
  const betaHref = userId ? "/dashboard" : "/sign-up";
  const betaLabel = userId ? "View dashboard" : "Get beta access";

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
              Marketworks helps you follow the strongest stocks in the Indian
              market — without watching it all day. You get three ready-made
              portfolios and a daily market read, built on live data instead of
              news and noise.
            </p>
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                href={betaHref}
                className="rounded-lg bg-primary px-6 py-3 text-base font-semibold text-primary-foreground transition-opacity hover:opacity-90"
              >
                {betaLabel}
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

        {/* Welcome + what Marketworks is (plain-language intro for newcomers) */}
        <section className="border-t border-border px-6 py-20 sm:px-12 sm:py-28">
          <div className="mx-auto flex max-w-[720px] flex-col gap-5">
            <span className="text-[13px] font-semibold uppercase tracking-[0.16em] text-primary">
              Welcome to the beta
            </span>
            <h2 className="font-serif text-[2rem] font-medium leading-[1.15] tracking-[-0.01em] text-foreground sm:text-[2.5rem]">
              New here? Here&apos;s the whole idea in a minute.
            </h2>
            <p className="text-lg leading-[1.65] text-muted-foreground">
              Thanks for being one of our first testers. Marketworks is a simpler
              way to invest in Indian stocks. Instead of picking names yourself
              or reacting to the news, you follow ready-made portfolios that are
              rebuilt on a fixed schedule — a &ldquo;rebalance&rdquo; — around the
              stocks that are currently leading the market.
            </p>
            <p className="text-lg leading-[1.65] text-muted-foreground">
              It all runs on one idea called <span className="text-foreground">momentum</span>:
              stocks that have been rising tend to keep leading for a while. Our
              system measures this across the market every week, so the
              portfolios quietly stay with the leaders and step away as they
              fade. No predictions, no hot takes — just a clear, rules-based list
              you can follow.
            </p>
          </div>
        </section>

        {/* How it works */}
        <section className="border-t border-border px-6 py-20 sm:px-12 sm:py-28">
          <div className="mx-auto flex max-w-[1080px] flex-col gap-12">
            <h2 className="max-w-[560px] font-serif text-[2rem] font-medium leading-[1.15] tracking-[-0.01em] text-foreground sm:text-[2.5rem]">
              How it works
            </h2>
            <div className="grid gap-12 sm:grid-cols-3">
              {STEPS.map((step, i) => (
                <div key={step.title} className="flex flex-col gap-3">
                  <span className="font-mono text-sm text-primary">
                    0{i + 1}
                  </span>
                  <h3 className="font-serif text-2xl font-medium leading-[1.2] text-foreground">
                    {step.title}
                  </h3>
                  <p className="text-[16px] leading-[1.6] text-muted-foreground">
                    {step.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* The research behind it — momentum as a factor + our quant work */}
        <section className="border-t border-border px-6 py-20 sm:px-12 sm:py-28">
          <div className="mx-auto flex max-w-[720px] flex-col gap-5">
            <span className="text-[13px] font-semibold uppercase tracking-[0.16em] text-primary">
              The research behind it
            </span>
            <h2 className="font-serif text-[2rem] font-medium leading-[1.15] tracking-[-0.01em] text-foreground sm:text-[2.5rem]">
              Process over prediction.
            </h2>
            <p className="text-lg leading-[1.65] text-muted-foreground">
              Momentum isn&apos;t a hunch. It&apos;s a{" "}
              <span className="text-foreground">factor</span> — one of a small
              handful of forces that decades of research have shown drive stock
              returns over time, alongside things like value and quality. Put
              simply: stocks that have been outperforming tend to keep
              outperforming for a while.
            </p>
            <p className="text-lg leading-[1.65] text-muted-foreground">
              What makes it worth building on is how stubbornly it persists —
              across decades, across markets, and notably in Indian equities.
              We&apos;ve spent years studying how it actually behaves here:
              testing it over long stretches of market history, validating it on
              periods our models had never seen, and stress-testing it through
              crashes, rallies, and quiet drifts. Only the rules that hold up on
              that unseen data earn a place in a portfolio.
            </p>
            <p className="text-lg leading-[1.65] text-muted-foreground">
              That&apos;s the whole philosophy:{" "}
              <span className="text-foreground">process over prediction</span>. We
              don&apos;t try to guess where the market is headed. We follow a
              disciplined, repeatable process that keeps each portfolio with the
              current leaders and steps away as they fade — the same way, every
              week, no matter the headlines.
            </p>
            <div className="pt-1">
              <Link
                href="/library/welcome_to_marketworks_beta"
                className="inline-flex items-center gap-2 text-base font-semibold text-primary transition-opacity hover:opacity-80"
              >
                Read the full story
                <span aria-hidden>→</span>
              </Link>
            </div>
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
                Three ways to follow momentum.
              </h2>
              <p className="max-w-[560px] text-lg leading-[1.6] text-muted-foreground">
                Each one is a rules-based list of Indian stocks, rebuilt on a
                schedule so it stays with the current leaders. Pick the style
                that fits you — steady growth, a calmer ride, or a quality tilt.
                These are model portfolios for research and education, not
                personalised advice.
              </p>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              {portfolios.map((universe) => (
                <PortfolioCard key={universe.id} universe={universe} />
              ))}
            </div>
            <div>
              <Link
                href="/portfolios"
                className="inline-flex items-center gap-2 text-base font-semibold text-primary transition-opacity hover:opacity-80"
              >
                Compare all three portfolios
                <span aria-hidden>→</span>
              </Link>
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
              Sign up to follow the three portfolios and the daily market read.
              Free while we&apos;re in beta.
            </p>
            <Link
              href={betaHref}
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
