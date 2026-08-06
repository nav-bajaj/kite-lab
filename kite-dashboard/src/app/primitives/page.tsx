import Link from "next/link";
import { Eye, ListChecks, TrendingUp } from "lucide-react";

import { UNIVERSES } from "@/lib/universes";
import { FloatingNav } from "@/components/marketing/floating-nav";
import {
  FactTile,
  SelectorPanel,
} from "@/components/marketing/selector-panel";
import {
  CollageCard,
  FeatureTile,
  FloatPanel,
  GhostRows,
  GrainCard,
  GuideCard,
  SectionHeader,
  StackCard,
} from "@/components/marketing/study-cards";

export const metadata = {
  title: "Primitives gallery — design_studies",
  robots: { index: false, follow: false },
};

/* design_studies loop 15: the card-primitive gallery. A study surface, not a
 * product page — the /primitives route is public ONLY on this branch (see
 * middleware note) and carries noindex. */

function Caption({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-4 mt-14 font-mono text-xs text-muted-foreground">
      {children}
    </p>
  );
}

export default function PrimitivesPage() {
  return (
    <div className="mw-brand mw-mint2 mw-sans-headings relative min-h-screen bg-surface-base">
      <FloatingNav />
      <main className="mx-auto max-w-[1140px] px-6 pb-28 pt-32">
        <h1 className="text-[2rem] font-semibold leading-[1.1] tracking-[-0.02em] text-foreground sm:text-[2.5rem]">
          Primitives gallery
        </h1>
        <p className="mt-3 max-w-[560px] text-base leading-[1.6] text-muted-foreground">
          Card experiments from the reference studies. Everything is
          token-derived; flip the palette in the nav to re-theme the whole
          sheet.
        </p>

        <Caption>
          01 · GrainCard — grainy corner wash, abstract glyph, guide lines
          (Google Fonts Knowledge reference)
        </Caption>
        <GrainCard glyph="m">
          <h2 className="text-2xl font-semibold tracking-[-0.01em] text-foreground sm:text-3xl">
            Momentum, explained
          </h2>
          <p className="mt-4 text-[15px] leading-[1.65] text-foreground/75">
            A home for the concepts behind the portfolios: what momentum is,
            why process beats prediction, and how a weekly rebalance quietly
            keeps you with the market&apos;s leaders.
          </p>
          <Link
            href="/library"
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-primary"
          >
            Browse the library <span aria-hidden>→</span>
          </Link>
        </GrainCard>

        <Caption>
          02 · StackCard — pastel stack with peeking layers, pill label, media
          slot (clay.com reference)
        </Caption>
        <StackCard
          label="Rebalance"
          media={
            <div className="relative h-full min-h-[220px] w-full overflow-hidden rounded-[20px] bg-[color-mix(in_oklab,var(--secondary)_18%,#ffffff)]">
              <div aria-hidden className="mw-grid-fade absolute inset-0" />
              <FloatPanel className="left-6 top-8 w-[52%]">
                <GhostRows rows={3} />
              </FloatPanel>
              <FloatPanel className="bottom-6 right-6 w-[44%]">
                <GhostRows rows={2} />
              </FloatPanel>
            </div>
          }
        >
          <h2 className="text-2xl font-semibold leading-[1.15] tracking-[-0.01em] sm:text-3xl">
            <span className="text-foreground">Rebuilt on schedule,</span>{" "}
            <span className="text-acc1-fg">not on headlines</span>
          </h2>
          <p className="mt-4 max-w-[42ch] text-[15px] leading-[1.65] text-muted-foreground">
            Every portfolio follows the same weekly discipline: score the
            market, keep the leaders, step away from the fades. No guessing in
            between.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/portfolios"
              className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
            >
              See the portfolios
            </Link>
            <Link
              href="/library"
              className="rounded-full border border-border bg-card px-5 py-2.5 text-sm font-semibold text-foreground"
            >
              How it works
            </Link>
          </div>
        </StackCard>

        <Caption>
          03 · CollageCard — color blob + overlapping floating panels, slots
          for real product UI (clay.com reference)
        </Caption>
        <CollageCard>
          <FloatPanel className="left-[8%] top-10 w-[46%]">
            <p className="mb-3 font-mono text-[11px] text-muted-foreground">
              holdings
            </p>
            <GhostRows rows={5} />
          </FloatPanel>
          <FloatPanel className="right-[7%] top-24 w-[34%]">
            <p className="mb-3 font-mono text-[11px] text-muted-foreground">
              weekly scores
            </p>
            <GhostRows rows={3} />
          </FloatPanel>
          <FloatPanel className="bottom-8 left-[30%] w-[30%]">
            <GhostRows rows={2} />
          </FloatPanel>
        </CollageCard>

        <Caption>
          04 · SectionHeader + FeatureTile row — centered opener, soft tiles
          (clay.com end-to-end reference)
        </Caption>
        <div className="rounded-[24px] border border-border/60 bg-card px-6 py-14 sm:px-10">
          <SectionHeader
            title="Momentum, done properly"
            sub="The system scores the whole market every week and keeps the portfolios with the leaders. No headlines, no hunches, no manual stock-picking."
            cta={{ href: "/sign-up", label: "Get beta access" }}
          />
          <div className="mt-12 grid gap-5 sm:grid-cols-3">
            <FeatureTile
              icon={<TrendingUp size={26} strokeWidth={1.75} aria-hidden />}
              title="We rank the market"
            >
              Every week our system scores stocks by momentum: the simple idea
              that names already trending up tend to keep leading for a while.
            </FeatureTile>
            <FeatureTile
              icon={<ListChecks size={26} strokeWidth={1.75} aria-hidden />}
              title="We build the portfolios"
            >
              The strongest names go into ready-made lists you can follow. When
              the leaders change, the list updates.
            </FeatureTile>
            <FeatureTile
              icon={<Eye size={26} strokeWidth={1.75} aria-hidden />}
              title="You follow along"
            >
              See exactly what each portfolio holds, what changed at the last
              rebalance, and why, all in plain language.
            </FeatureTile>
          </div>
        </div>

        <Caption>
          05 · GuideCard — framed media, tag pill, footer meta (clay.com
          guides reference); frames rotate accent colors
        </Caption>
        <div className="grid gap-8 sm:grid-cols-2">
          <GuideCard
            href="/library"
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
            Welcome to the beta: how the portfolios, the weekly rebalance, and
            the daily market read fit together.
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
            The headline this week was not the rupee, but the rupee is quietly
            making everything imported a little more expensive.
          </GuideCard>
        </div>

        <Caption>
          06 · SelectorPanel + FactTile — interactive pills with a detail
          surface (clay.com signal-picker reference); real portfolio data
        </Caption>
        <SelectorPanel
          lead="Pick a portfolio to see what it follows and who it suits"
          footnote="Each portfolio is a rules-based list, rebuilt on schedule. Model portfolios for research and education, not personalised advice."
          items={Object.values(UNIVERSES)
            .filter((u) => u.clientVisible)
            .map((u) => ({
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
                </div>
              ),
            }))}
        />

        <Caption>
          07 · GridFadeSection — the teak.io grid that fades in and out with
          scroll (scroll-driven where supported; static edge fade otherwise)
        </Caption>
        <section className="relative overflow-hidden rounded-[24px] border border-border/60 bg-card">
          <div aria-hidden className="mw-grid-fade absolute inset-0" />
          <div className="relative px-8 py-24 text-center sm:py-32">
            <h2 className="text-2xl font-semibold tracking-[-0.01em] text-foreground sm:text-3xl">
              A section on the fading grid
            </h2>
            <p className="mx-auto mt-3 max-w-[46ch] text-[15px] leading-[1.6] text-muted-foreground">
              Scroll this page: the grid breathes in as the section enters the
              viewport and out as it leaves. On browsers without scroll-driven
              animations it keeps the soft edge fade.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
