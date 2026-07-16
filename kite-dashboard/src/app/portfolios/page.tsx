import Link from "next/link";

import { getUniverse } from "@/lib/universes";
import type { UniverseId } from "@/lib/types";
import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export const metadata = {
  title: "Portfolios — Marketworks",
  description:
    "Three ready-made momentum portfolios for Indian stocks — Core Momentum, " +
    "Defensive Blend, and Quality Momentum. See what each one does, how often " +
    "it updates, and who it suits, in plain language.",
};

// Plain-language detail for each portfolio, written for a newcomer. Grounded in
// docs/portfolios.md (strategy, universe, cadence) — display names, stock
// counts and risk tags come from src/lib/universes.ts. No performance figures
// on this public page; these are educational descriptions, not advice.
type PortfolioDetail = {
  tag: string;
  what: string;
  cadence: string;
  holds: string;
  forWho: string;
};

// Keyed by a Map (not a Record) so lookups use `.get()` — avoids the
// object-injection lint sink that dynamic Record indexing trips.
const DETAILS = new Map<UniverseId, PortfolioDetail>([
  ["l6_v2", {
    tag: "For growth",
    what:
      "Our flagship. Core Momentum holds the strongest-trending stocks from " +
      "across the broad Indian market. Every week the list is rebuilt so it " +
      "stays with the current leaders and drops names as they lose steam. It " +
      "keeps no cash aside and does not try to time the market — it simply " +
      "follows the leaders, fully invested.",
    cadence: "Rebuilt every week",
    holds: "24 stocks, chosen from the NSE 500 (India's 500 largest listed companies)",
    forWho:
      "People who want the most direct way to ride the market's leaders, and " +
      "are comfortable with bigger ups and downs in exchange for higher growth " +
      "potential.",
  }],
  ["combo_defensive", {
    tag: "For a calmer ride",
    what:
      "The steadier option. Defensive Blend combines our other two strategies " +
      "and adds one safety feature: when the overall market turns weak, it " +
      "moves half the portfolio to cash to soften the fall. The trade-off is " +
      "giving up a little upside in strong markets in return for smaller drops " +
      "in bad ones.",
    cadence: "Rebuilt every two weeks",
    holds: "Up to 24 stocks, blended from across the NSE 500, with a cash cushion in weak markets",
    forWho:
      "People who like the idea of following momentum but want a smoother " +
      "experience and smaller losses when markets get rough.",
  }],
  ["om25_v3", {
    tag: "For a quality tilt",
    what:
      "Momentum, with a preference for sturdier companies. Quality Momentum " +
      "looks for stocks that are trending up and tend to hold their ground " +
      "better when markets fall, and it automatically turns more defensive " +
      "when the market weakens. It runs on India's larger and mid-sized " +
      "companies.",
    cadence: "Rebuilt every two weeks",
    holds: "25 stocks, chosen from the Nifty 250 (large and mid-sized companies)",
    forWho:
      "People who want to follow momentum but prefer steadier, better-" +
      "established businesses over the raciest names.",
  }],
  // Trend Leaders (tl25_v3) and the admin-only legacy universes are
  // intentionally absent — no public detail during the beta.
]);

// Display order on this page (flagship first). Only client-visible portfolios
// with plain-language detail are shown.
const ORDER: UniverseId[] = ["l6_v2", "combo_defensive", "om25_v3"];

export default function PortfoliosPage() {
  const portfolios = ORDER.map((id) => ({
    universe: getUniverse(id),
    detail: DETAILS.get(id),
  })).filter(
    (p): p is { universe: ReturnType<typeof getUniverse>; detail: PortfolioDetail } =>
      p.universe.clientVisible && p.detail !== undefined,
  );

  return (
    <div className="mw-brand flex min-h-screen flex-col bg-background">
      <MarketingNav active="Portfolios" />

      <main className="flex-1">
        {/* Hero */}
        <section className="px-6 py-24 sm:px-12 sm:py-28">
          <div className="mx-auto flex max-w-[720px] flex-col gap-6">
            <span className="text-[13px] font-semibold uppercase tracking-[0.16em] text-primary">
              The portfolios
            </span>
            <h1 className="font-serif text-[2.5rem] font-medium leading-[1.08] tracking-[-0.02em] text-foreground sm:text-[3.5rem]">
              Three ready-made ways to follow the market.
            </h1>
            <p className="text-xl leading-[1.6] text-muted-foreground">
              Each portfolio is a plain list of Indian stocks that our system
              rebuilds on a fixed schedule — a &ldquo;rebalance&rdquo; — so it
              keeps holding the names that are currently leading the market. They
              all run on the same idea, momentum, but with different levels of
              risk. Pick the one that fits how you like to invest.
            </p>
          </div>
        </section>

        {/* Portfolio detail cards */}
        <section className="border-t border-border px-6 py-16 sm:px-12 sm:py-20">
          <div className="mx-auto flex max-w-[820px] flex-col gap-6">
            {portfolios.map(({ universe, detail }) => {
              return (
                <article
                  key={universe.id}
                  className="flex flex-col gap-5 rounded-2xl border border-border bg-card p-7 sm:p-9"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                      {detail.tag}
                    </span>
                    <span className="font-mono text-sm text-muted-foreground">
                      {universe.stocks} stocks
                    </span>
                  </div>

                  <h2 className="font-serif text-[1.75rem] font-medium leading-[1.15] text-foreground">
                    {universe.name}
                  </h2>

                  <p className="text-[17px] leading-[1.62] text-[color:var(--brand-prose)]">
                    {detail.what}
                  </p>

                  <dl className="grid gap-x-8 gap-y-4 border-t border-border pt-5 sm:grid-cols-2">
                    <div className="flex flex-col gap-1">
                      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        How often it updates
                      </dt>
                      <dd className="text-[15px] text-foreground">{detail.cadence}</dd>
                    </div>
                    <div className="flex flex-col gap-1">
                      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        What it holds
                      </dt>
                      <dd className="text-[15px] text-foreground">{detail.holds}</dd>
                    </div>
                    <div className="flex flex-col gap-1 sm:col-span-2">
                      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Who it&apos;s for
                      </dt>
                      <dd className="text-[15px] leading-[1.55] text-foreground">
                        {detail.forWho}
                      </dd>
                    </div>
                  </dl>
                </article>
              );
            })}

            <div className="flex flex-col gap-3 border-t border-border pt-8">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                Process over prediction
              </span>
              <p className="max-w-[620px] text-[15px] leading-[1.6] text-foreground">
                All three are built from the same research: momentum tested over
                years of Indian market history and validated on data our models
                had never seen. We don&apos;t predict where the market is going —
                we run a disciplined process that stays with the leaders and
                steps away as they fade.{" "}
                <Link
                  href="/"
                  className="font-medium text-primary underline-offset-2 hover:underline"
                >
                  More on the thinking →
                </Link>
              </p>
            </div>

            <p className="max-w-[620px] text-[15px] leading-[1.6] text-muted-foreground">
              These are model portfolios for research and education — a
              transparent look at what a rules-based momentum strategy would
              hold. They are not personalised advice or a recommendation to buy
              or sell any stock, and all investing carries risk.
            </p>
          </div>
        </section>

        {/* CTA band */}
        <section className="px-6 py-20 sm:px-12 sm:py-24">
          <div className="mx-auto flex max-w-[820px] flex-col items-start gap-6 rounded-2xl bg-primary px-8 py-14 sm:px-14">
            <h2 className="max-w-[620px] font-serif text-[2rem] font-medium leading-[1.15] text-primary-foreground sm:text-[2.5rem]">
              See the live portfolios.
            </h2>
            <p className="max-w-[560px] text-lg leading-[1.6] text-primary-foreground/85">
              Sign up to follow all three — see exactly what each one holds and
              what changed at the last rebalance. Free while we&apos;re in beta.
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
