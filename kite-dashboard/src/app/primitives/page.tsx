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
import {
  ExhibitFrame,
  PipelineDiagram,
  ScrambleIn,
  SectionMeter,
  StatTable,
} from "@/components/marketing/instrument-primitives";
import {
  InkBand,
  InkCard,
  MethodMark,
  ProofMosaic,
  SignalBoard,
  SignalChips,
  StackSection,
  TexturePanel,
  TexturedFooter,
} from "@/components/marketing/composition-primitives";
import { AccordionShowcase } from "@/components/marketing/accordion-showcase";
import { HeroFlow } from "@/components/marketing/hero-flow";

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
    <div className="mw-brand mw-mint2 mw-serif-headings relative min-h-screen bg-surface-base">
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

        <Caption>
          08 · SectionMeter — the metered index header (AEYE_STUDY D4);
          evolves the mono section captions into instrument telemetry
        </Caption>
        <div className="space-y-10 rounded-[24px] border border-border/60 bg-card px-6 py-10 sm:px-10">
          <div>
            <SectionMeter index={2} total={5} label="How it works" />
            <h2 className="mt-6 text-2xl font-semibold tracking-[-0.01em] text-foreground sm:text-3xl">
              Momentum, done properly
            </h2>
          </div>
          <div>
            <SectionMeter index={4} total={5} label="The portfolios" />
            <h2 className="mt-6 text-2xl font-semibold tracking-[-0.01em] text-foreground sm:text-3xl">
              Three ways to follow momentum
            </h2>
          </div>
        </div>

        <Caption>
          09 · StatTable — figures in hairline cells, no cards (AEYE_STUDY
          D5); real Quality Momentum record
        </Caption>
        <StatTable
          cells={[
            { value: "44.78%", label: "CAGR", note: "compounded annual return" },
            { value: "1.86", label: "Sharpe", note: "return per unit of risk" },
            { value: "−36.6%", label: "Max drawdown", note: "printed beside returns" },
            { value: "9.3y", label: "Validation window", note: "rules never re-tuned" },
          ]}
          footnote="Quality Momentum · out-of-sample 2017–2026 · net of 0.2% per-trade slippage · Nifty 250"
        />

        <Caption>
          10 · PipelineDiagram — the real daily pipeline as labelled nodes on
          a dotted canvas (AEYE_STUDY D10); one light travels the rail,
          static under reduced motion
        </Caption>
        <PipelineDiagram />

        <Caption>
          11 · ExhibitFrame — corner-tick framing for charts and media
          (AEYE_STUDY D8); shown around the HeroFlow signal field
        </Caption>
        <ExhibitFrame
          label="Exhibit — signal field"
          caption="The homepage flow-field canvas inside the frame; any chart, screenshot, or media slots in the same way."
        >
          <div className="relative h-[300px] w-full overflow-hidden rounded-[16px] border border-border/60 bg-card">
            <div aria-hidden className="mw-grid-fade absolute inset-0" />
            <HeroFlow className="absolute inset-0" />
          </div>
        </ExhibitFrame>

        <Caption>
          12 · ScrambleIn — the single decode moment (AEYE_STUDY D3,
          rationed: once per page); scroll it into view to trigger, refresh
          to replay
        </Caption>
        <div className="rounded-[24px] border border-border/60 bg-card px-6 py-16 text-center sm:px-10">
          <h2 className="text-2xl font-semibold tracking-[-0.01em] text-foreground sm:text-4xl">
            <ScrambleIn text="Rebuilt on schedule, not on headlines." />
          </h2>
          <p className="mx-auto mt-4 max-w-[46ch] text-[15px] leading-[1.6] text-muted-foreground">
            One authored decode per page. On every heading it would be the
            template&apos;s personality; used once it is ours.
          </p>
        </div>

        <Caption>
          13 · TexturePanel — generative card-media backdrops in four
          variants (PERCEPT P2); the parked asset-study fields, re-homed at
          card scale
        </Caption>
        <div className="grid gap-5 sm:grid-cols-2">
          {(
            [
              ["dither", "stepped bayer dots"],
              ["drift", "cumulative curves"],
              ["contour", "terrain rings"],
              ["hatch", "fine diagonal fade"],
            ] as const
          ).map(([variant, note]) => (
            <div
              key={variant}
              className="relative h-[200px] overflow-hidden rounded-[16px] border border-border/60 bg-card"
            >
              <TexturePanel variant={variant} />
              <span className="absolute bottom-4 left-4 rounded-full border border-border bg-background px-3 py-1 font-mono text-[11px] text-muted-foreground">
                {variant} · {note}
              </span>
            </div>
          ))}
        </div>

        <Caption>
          14 · SignalChips — real pipeline events as ambient rows, one
          highlighted (PERCEPT P4 × the aeye tape); drifts gently, static
          under reduced motion
        </Caption>
        <div className="rounded-[24px] border border-border/60 bg-card px-4 py-8">
          <SignalChips />
        </div>

        <Caption>
          15 · ProofMosaic — the record as one tile wall: real stats, method
          facts, the rejected ledger, real library titles (clay K3, no
          invented logos or quotes)
        </Caption>
        <ProofMosaic />

        <Caption>
          16 · MethodMark — institutional facts as rose-curve roundels (clay
          K6 in our line-work; the certificate seal at badge scale)
        </Caption>
        <div className="flex flex-wrap items-center justify-center gap-10 rounded-[24px] border border-border/60 bg-card px-6 py-10">
          <MethodMark lines={["OOS", "2017–26"]} />
          <MethodMark lines={["NET OF", "SLIPPAGE"]} />
          <MethodMark lines={["20% DD", "STOP"]} />
          <MethodMark lines={["1/N", "WEIGHT"]} />
        </div>

        <Caption>
          17 · InkBand + InkCard + dark SignalChips — the sustained dark
          movement (PERCEPT P3) on the green-deep drench token; one per page
        </Caption>
        <InkBand>
          <p className="font-mono text-xs uppercase tracking-[0.14em] text-[color-mix(in_oklab,var(--surface-panel-deep-foreground)_60%,transparent)]">
            Why a system
          </p>
          <h2 className="mt-3 max-w-[22ch] text-3xl font-semibold leading-[1.15] sm:text-4xl">
            Discipline is the product
          </h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            <InkCard title="Rules, written down">
              Entries, exits, and sizing decided before the market opens ever
              factor into it.
            </InkCard>
            <InkCard title="Validated out of sample">
              Tuned on 2009–2016, then left alone and judged on the next 9.3
              years.
            </InkCard>
            <InkCard title="Drawdowns, shown">
              −36.6% is printed beside 44.78% wherever the record appears.
            </InkCard>
          </div>
          <div className="mt-10">
            <SignalChips dark />
          </div>
        </InkBand>

        <Caption>
          18 · AccordionShowcase — synced accordion + swapping visual
          (PERCEPT P5); texture stand-ins until real product screenshots land
        </Caption>
        <div className="rounded-[24px] border border-border/60 bg-card px-6 py-10 sm:px-10">
          <AccordionShowcase />
        </div>

        <Caption>
          19 · SignalBoard — the real table as hero media (clay K4): the
          2026-05-12 record with a highlighted top row under portfolio pills
        </Caption>
        <div className="rounded-[24px] border border-border/60 bg-surface-panel-mist px-6 py-10 sm:px-10">
          <SignalBoard className="mx-auto max-w-[640px]" />
        </div>

        <Caption>
          20 · StackSection ×3 — clay&apos;s sticky-stacking sections,
          colour-rule-resolved: panels stay white / soft / wash, triads live
          in the elements (scroll through to feel the stack)
        </Caption>
        <div>
          <StackSection tone="card">
            <SectionMeter index={1} total={3} label="The idea" />
            <h2 className="mt-8 max-w-[18ch] text-3xl font-semibold leading-[1.15] sm:text-4xl">
              Stocks already leading tend to keep leading
            </h2>
            <p className="mt-4 max-w-[52ch] text-[15px] leading-[1.65] text-muted-foreground">
              Momentum is one of the most documented effects in markets. The
              hard part is following it with discipline — that is the product.
            </p>
          </StackSection>
          <StackSection tone="soft">
            <SectionMeter index={2} total={3} label="The system" />
            <h2 className="mt-8 max-w-[18ch] text-3xl font-semibold leading-[1.15] sm:text-4xl">
              Scored weekly, rebuilt on schedule
            </h2>
            <p className="mt-4 max-w-[52ch] text-[15px] leading-[1.65] text-muted-foreground">
              The whole NSE 500 is ranked every week; portfolios keep the
              leaders and step away from the fades. No headlines in between.
            </p>
          </StackSection>
          <StackSection tone="wash">
            <SectionMeter index={3} total={3} label="The record" />
            <h2 className="mt-8 max-w-[18ch] text-3xl font-semibold leading-[1.15] sm:text-4xl">
              Judged on years it never saw
            </h2>
            <p className="mt-4 max-w-[52ch] text-[15px] leading-[1.65] text-muted-foreground">
              44.78% CAGR with a −36.6% drawdown, out of sample, net of
              slippage. Both numbers, same ink.
            </p>
          </StackSection>
        </div>

        <Caption>
          21 · TexturedFooter — the merged CTA + footer mega-section on
          textured green-deep with the giant wordmark (PERCEPT P8)
        </Caption>
        <TexturedFooter />
      </main>
    </div>
  );
}
