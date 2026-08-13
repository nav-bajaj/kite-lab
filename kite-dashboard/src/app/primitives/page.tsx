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
  GhostPill,
  InkBand,
  InkCard,
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
    <div className="mw-brand mw-serif-headings relative min-h-screen bg-surface-base">
      <FloatingNav />
      <main className="mx-auto max-w-[1140px] px-6 pb-28 pt-32">
        <h1 className="text-[2rem] font-medium leading-[1.15] text-foreground sm:text-[2.5rem]">
          Primitives gallery
        </h1>
        <p className="mt-3 max-w-[560px] text-base leading-[1.6] text-muted-foreground">
          Card experiments from the reference studies, on the set system:
          single green, Libre Baskerville, IBM Plex Mono. Everything is
          token-derived; the sun/moon toggle re-themes the sheet.
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
          13 · TexturePanel — card-media backdrops, curated set (founder cut
          drift + contour; grid + dots added). Textures + masked fades do the
          richness work; no decorative colour gradients on light surfaces
        </Caption>
        <div className="grid gap-5 sm:grid-cols-2">
          {(
            [
              ["dither", "stepped bayer dots"],
              ["hatch", "fine diagonal fade"],
              ["grid", "chart paper"],
              ["dots", "pipeline lattice"],
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
          highlighted; dot colour encodes kind (green = portfolio event,
          sky = system event); drifts gently, static under reduced motion
        </Caption>
        <div className="rounded-[24px] border border-border/60 bg-card px-4 py-8">
          <SignalChips />
        </div>

        <Caption>
          15 · ProofMosaic — the record as one tile wall; each cell KIND
          carries its triad (stats = ink on card, method = sun wash,
          rejected = coral, library = purple) — accents encoding structure
        </Caption>
        <ProofMosaic />

        <Caption>
          16 · InkBand + InkCard + dark SignalChips — the sustained dark
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
          17 · AccordionShowcase — synced accordion + swapping visual
          (PERCEPT P5); texture stand-ins until real product screenshots land
        </Caption>
        <div className="rounded-[24px] border border-border/60 bg-card px-6 py-10 sm:px-10">
          <AccordionShowcase />
        </div>

        <Caption>
          18 · SignalBoard — the real table as hero media; the pills carry
          the proposed portfolio identity hues (Core = green, Quality = sun,
          Trend = sky, Defensive = purple — one hue per portfolio, site-wide)
        </Caption>
        <div className="rounded-[24px] border border-border/60 bg-surface-panel-mist px-6 py-10 sm:px-10">
          <SignalBoard className="mx-auto max-w-[640px]" />
        </div>

        <Caption>
          19 · StackSection, clay-committed (founder amendment): sibling
          section cards take the FULL triad — tint ground, deep ink, vivid
          marks — one hue per portfolio (the identity hues), white page
          between. Scroll through the stack
        </Caption>
        <div>
          <StackSection accent={1}>
            <GhostPill accent={1}>Core Momentum</GhostPill>
            <h2 className="mt-7 max-w-[20ch] text-3xl font-semibold leading-[1.15] text-acc1-fg sm:text-4xl">
              The flagship: pure momentum, rebuilt weekly
            </h2>
            <p className="mt-4 max-w-[52ch] text-[15px] leading-[1.65] text-acc1-fg/80">
              Six-month momentum scaled by volatility across the NSE 500.
              The highest-CAGR system, and the most demanding of nerve.
            </p>
            <div className="mt-8 grid max-w-[560px] gap-5 sm:grid-cols-3">
              <div>
                <p className="font-mono text-2xl text-acc1-fg [font-variant-numeric:tabular-nums]">59.4%</p>
                <p className="mt-1 text-xs text-acc1-fg/70">CAGR · Jul 2020–Feb 2026</p>
              </div>
              <div>
                <p className="font-mono text-2xl text-acc1-fg [font-variant-numeric:tabular-nums]">1.92</p>
                <p className="mt-1 text-xs text-acc1-fg/70">Sharpe</p>
              </div>
              <div>
                <p className="font-mono text-2xl text-acc1-fg [font-variant-numeric:tabular-nums]">−30.0%</p>
                <p className="mt-1 text-xs text-acc1-fg/70">max drawdown · shown</p>
              </div>
            </div>
            <div className="relative mt-8 h-[160px] overflow-hidden rounded-[18px] bg-card/60">
              <TexturePanel variant="grid" toneClassName="text-acc1-line" />
            </div>
            <a
              href="/portfolios"
              className="mt-8 inline-block rounded-full bg-acc1-fg px-6 py-3 text-sm font-semibold text-acc1"
            >
              Explore the record
            </a>
          </StackSection>
          <StackSection accent={2}>
            <GhostPill accent={2}>Quality Momentum</GhostPill>
            <h2 className="mt-7 max-w-[20ch] text-3xl font-semibold leading-[1.15] text-acc2-fg sm:text-4xl">
              Validated on nine years it never saw
            </h2>
            <p className="mt-4 max-w-[52ch] text-[15px] leading-[1.65] text-acc2-fg/80">
              Capture asymmetry with a regime tilt on the Nifty 250 — tuned on
              2009–2016, then judged untouched on 2017–2026.
            </p>
            <div className="mt-8 grid max-w-[560px] gap-5 sm:grid-cols-3">
              <div>
                <p className="font-mono text-2xl text-acc2-fg [font-variant-numeric:tabular-nums]">44.78%</p>
                <p className="mt-1 text-xs text-acc2-fg/70">CAGR · out of sample</p>
              </div>
              <div>
                <p className="font-mono text-2xl text-acc2-fg [font-variant-numeric:tabular-nums]">1.86</p>
                <p className="mt-1 text-xs text-acc2-fg/70">Sharpe</p>
              </div>
              <div>
                <p className="font-mono text-2xl text-acc2-fg [font-variant-numeric:tabular-nums]">−36.6%</p>
                <p className="mt-1 text-xs text-acc2-fg/70">max drawdown · shown</p>
              </div>
            </div>
            <div className="relative mt-8 h-[160px] overflow-hidden rounded-[18px] bg-card/60">
              <TexturePanel variant="dither" toneClassName="text-acc2-line" />
            </div>
            <a
              href="/portfolios"
              className="mt-8 inline-block rounded-full bg-acc2-fg px-6 py-3 text-sm font-semibold text-acc2"
            >
              Explore the record
            </a>
          </StackSection>
          <StackSection accent={3}>
            <GhostPill accent={3}>Trend Leaders</GhostPill>
            <h2 className="mt-7 max-w-[20ch] text-3xl font-semibold leading-[1.15] text-acc3-fg sm:text-4xl">
              Three measures of trend quality, one list
            </h2>
            <p className="mt-4 max-w-[52ch] text-[15px] leading-[1.65] text-acc3-fg/80">
              Persistence above the 100-day average, drawdown control, and
              ranked momentum across the NSE 500.
            </p>
            <div className="mt-8 grid max-w-[560px] gap-5 sm:grid-cols-3">
              <div>
                <p className="font-mono text-2xl text-acc3-fg [font-variant-numeric:tabular-nums]">34.86%</p>
                <p className="mt-1 text-xs text-acc3-fg/70">CAGR · out of sample</p>
              </div>
              <div>
                <p className="font-mono text-2xl text-acc3-fg [font-variant-numeric:tabular-nums]">1.53</p>
                <p className="mt-1 text-xs text-acc3-fg/70">Sharpe</p>
              </div>
              <div>
                <p className="font-mono text-2xl text-acc3-fg [font-variant-numeric:tabular-nums]">−39.0%</p>
                <p className="mt-1 text-xs text-acc3-fg/70">max drawdown · shown</p>
              </div>
            </div>
            <div className="relative mt-8 h-[160px] overflow-hidden rounded-[18px] bg-card/60">
              <TexturePanel variant="dots" toneClassName="text-acc3-line" />
            </div>
            <a
              href="/portfolios"
              className="mt-8 inline-block rounded-full bg-acc3-fg px-6 py-3 text-sm font-semibold text-acc3"
            >
              Explore the record
            </a>
          </StackSection>
          <StackSection accent={5}>
            <GhostPill accent={5}>Defensive Blend</GhostPill>
            <h2 className="mt-7 max-w-[20ch] text-3xl font-semibold leading-[1.15] text-acc5-fg sm:text-4xl">
              Built for staying in the game
            </h2>
            <p className="mt-4 max-w-[52ch] text-[15px] leading-[1.65] text-acc5-fg/80">
              A 50/50 blend of Core and Quality Momentum ranks that halves
              allocation when the market regime turns bearish.
            </p>
            <div className="mt-8 grid max-w-[560px] gap-5 sm:grid-cols-3">
              <div>
                <p className="font-mono text-2xl text-acc5-fg [font-variant-numeric:tabular-nums]">50/50</p>
                <p className="mt-1 text-xs text-acc5-fg/70">component blend</p>
              </div>
              <div>
                <p className="font-mono text-2xl text-acc5-fg [font-variant-numeric:tabular-nums]">−50%</p>
                <p className="mt-1 text-xs text-acc5-fg/70">bear-regime allocation</p>
              </div>
              <div>
                <p className="font-mono text-2xl text-acc5-fg [font-variant-numeric:tabular-nums]">3-day</p>
                <p className="mt-1 text-xs text-acc5-fg/70">regime confirmation</p>
              </div>
            </div>
            <div className="relative mt-8 h-[160px] overflow-hidden rounded-[18px] bg-card/60">
              <TexturePanel variant="hatch" toneClassName="text-acc5-line" />
            </div>
            <a
              href="/portfolios"
              className="mt-8 inline-block rounded-full bg-acc5-fg px-6 py-3 text-sm font-semibold text-acc5"
            >
              Explore the record
            </a>
          </StackSection>
        </div>

        <Caption>
          20 · TexturedFooter — the merged CTA + footer mega-section on
          textured green-deep with the giant wordmark (PERCEPT P8)
        </Caption>
        <TexturedFooter />
      </main>
    </div>
  );
}
