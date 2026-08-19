# Momentum Investing: Five-Reel Series — Content OS Run

This is the architecture-generated version of the series. All five frames and
spoken scripts were founder-approved on 19 August 2026. The original draft is
preserved separately in `momentum_reels_5.md` for comparison.

## Series brief

- **Audience:** Karan — an Indian investor who owns or selects stocks but does
  not yet have a repeatable framework.
- **Purpose:** Explain momentum investing and introduce quantitative,
  rules-based portfolios without turning the series into stock advice.
- **Language:** Simple, conversational and define-on-use.
- **Runtime:** Approximately 73–79 seconds of speech per reel, with edit pauses
  taking the finished videos to approximately 78–88 seconds.
- **Content boundary:** No stock recommendations, performance claims, invented
  examples, or precise return statistics.
- **Series progression:** observable strength → why trends may persist → what a
  quantitative rule does → how rebalancing works → where momentum can fail.

## Production grammar

All reels are `9:16` and use only these three layouts:

1. **Full-screen talking head (`TH`)** — fixed studio desk, direct to camera.
2. **Vertical stacked split (`STACK`)** — speaker above by default and graphics
   below. The composition is never side by side.
3. **Full-screen graphics canvas (`GC`)** — cards, rankings, conceptual charts
   and restrained abstractions.

```text
┌────────────────────┐
│                    │
│      SPEAKER       │  about 44%
│                    │
├────────────────────┤
│                    │
│  GRAPHICS CANVAS   │  about 56%
│                    │
└────────────────────┘
```

- Rows below describe narrative beats. Add a cut, crop change, emphasis mark,
  or canvas move every 4–5 seconds within longer rows.
- Captions appear phrase by phrase and remain clear of platform controls.
- Use the existing Marketworks design tokens and a small persistent wordmark.
- Charts without sourced series are conceptual, contain no fabricated values,
  and carry `Illustration only` when shown full-screen.
- Use emphasis marks only to direct attention: circle, underline, highlight or
  restrained ping.
- No rockets, coins, fake trading terminals, red crash treatments, decorative
  candlesticks, or generic trading-floor footage.

---

## Reel 1 — Momentum starts after the move

**Cover:** Does momentum notice a stock before it rises?

**Frame:** Momentum starts after a move has begun, because recent strength is
the evidence the strategy measures.

**Runtime:** 200 words · approximately 74 seconds spoken · 78 seconds edited

**Quality gate:** 36/40, pass

### Approved spoken script

**HOOK**

> A stock you own has started rising. Is that enough for a momentum rule to
> notice it? Only once the move is visible can the strategy start measuring it.

**BODY 1**

> Momentum is the tendency for stocks that have done better than their peers to
> keep doing better for a while, on average. Those last two words matter because
> plenty of strong stocks still reverse.

**BODY 2**

> A rules-based strategy begins with stocks that trade often enough to buy and
> sell easily. It measures every stock over the same period, compares each one
> with the rest, and ranks the results. A stock can rise and still rank poorly
> if most of its peers rose more.

**BODY 3**

> That is why momentum differs from chasing a sudden jump. One exciting day or
> a burst of social-media attention is not enough. The move has to happen before
> the strategy can measure it, and that delay is built into the idea.

**BODY 4**

> Momentum has no advance knowledge of the next move. It follows strength that
> already exists and updates when that evidence changes.

**TAKEAWAY**

> So once a stock has moved, momentum asks one question: has it become a genuine
> leader among its peers?

**CTA**

> Follow @marketworks.in for daily reads on Indian markets.

### Storyboard

| # | Time | Layout and cut | Spoken cue | Picture, overlay and motion | Build |
|---|---|---|---|---|---|
| 1 | `00:00–00:10` | `TH` → `STACK` on the question | “A stock you own has started rising…” | Begin clean to camera. On “started rising,” a restrained line path enters the lower canvas. Add an emphasis circle only when the question lands. Overlay: `A stock you own is rising.` | Premiere + AE |
| 2 | `00:10–00:20` | `GC` → `STACK` | “Only once the move is visible…” through “on average” | The line moves first; only then does a measuring window appear. Transition to peer cards moving at different rates. Overlay: `Only once the move is visible.` Then: `on average`. | Remotion |
| 3 | `00:20–00:28` | `TH`, tighter | “Those last two words matter…” | Remove the chart so the caveat stays with the speaker. Phrase caption: `plenty of strong stocks still reverse`. | Premiere |
| 4 | `00:28–00:48` | `GC` persistent canvas → `STACK` | “stocks that trade often enough…” through the peer comparison | Build three fixed zones: `Same period` → `Compare with the rest` → `Rank`. Finish on two illustrative lines that both rise, with the peer line rising more. Overlay: `Up, but still behind its peers.` | Remotion |
| 5 | `00:48–01:04` | `TH` → `GC` comparison | “momentum differs from chasing…” | Reveal `One exciting day is not enough.` Cut to a two-state canvas: one sudden spike/social pulse versus a longer measured path and peer ranking. | AE + Remotion |
| 6 | `01:04–01:13` | `TH` | “Momentum has no advance knowledge…” | Underline `strength that already exists`, then fade the mark when the evidence changes. | Premiere + AE |
| 7 | `01:13–01:18` | `TH` → end card | Takeaway + CTA | Hold eye contact for the question. End card: `A genuine leader among its peers?` followed by the wordmark and `@marketworks.in`. | Premiere |

**Asset call:** No AI b-roll. The measuring-window and peer-comparison graphics
carry the explanation more clearly.

---

## Reel 2 — Why momentum can persist

**Cover:** Why might the first move not be the last?

**Frame:** A price trend can persist because the market often absorbs a real
change in stages.

**Runtime:** 197 words · approximately 73 seconds spoken · 78 seconds edited

**Quality gate:** 35/40, pass

### Approved spoken script

**HOOK**

> A company you own reports better results, and the stock starts moving. Why
> might that first move be the beginning of the market changing its mind?

**BODY 1**

> Some investors react to the first update. Others notice it later, or wait for
> another result before changing their view. Some may not see the change until
> the company reports again. The old view does not disappear from the market in
> a single day.

**BODY 2**

> The price adjusts as those decisions arrive. The first move gets attention.
> Later updates may give more investors enough confidence to let go of the old
> view, so one piece of information can affect the stock over several stages.

**BODY 3**

> One explanation researchers have tested is that company information doesn't
> reach everyone, or convince everyone, at the same time. A trend can continue
> while the market is still changing its mind.

**BODY 4**

> This explanation cannot promise what any stock does next. The business can
> disappoint, or expectations can run too far before that gradual process
> finishes.

**TAKEAWAY**

> So why can a stock that has already moved keep moving? The first price move
> may simply be the market beginning to change its mind.

**CTA**

> Follow @marketworks.in for daily reads on Indian markets.

### Storyboard

| # | Time | Layout and cut | Spoken cue | Picture, overlay and motion | Build |
|---|---|---|---|---|---|
| 1 | `00:00–00:12` | `TH` → `STACK` | “A company you own reports better results…” | Open to camera. Lower canvas shows a `Company update` card and a price path beginning to move. The question appears phrase by phrase: `The beginning of the market changing its mind?` | Premiere + AE |
| 2 | `00:12–00:28` | `STACK`, speaker above | “Some investors react…” through “reports again” | Three groups enter one timeline at different moments: `reacts now`, `notices later`, `waits for another result`. The active group receives one restrained ping. Optional four-second research-desk b-roll can occupy the lower canvas. | AE / optional AI b-roll |
| 3 | `00:28–00:48` | `GC` information-ripple canvas | “The old view does not disappear…” through “several stages” | An `Old view` layer fades gradually. One update moves through three translucent rings; the illustrative price path advances in steps as each ring activates. Overlay: `One update. Several stages.` | Remotion |
| 4 | `00:48–01:01` | `TH` → `STACK` | “One explanation researchers have tested…” | Keep the claim with the speaker first. The lower canvas then shows the same information reaching groups at different times. Overlay: `One researched explanation`. | Premiere + AE |
| 5 | `01:01–01:09` | `TH`, tighter | “This explanation cannot promise…” | Remove motion graphics. Caption: `An explanation, not a promise.` No warning icons. | Premiere |
| 6 | `01:09–01:15` | `GC` → `TH` | “The first price move may simply be…” | Replay the first small step; keep later steps ghosted rather than predicted. Return to the speaker on “changing its mind.” | Remotion + Premiere |
| 7 | `01:15–01:18` | End card | CTA | Small wordmark and `@marketworks.in`. | Premiere |

### Optional AI b-roll prompt

> Documentary-style slow push-in on a quiet investment-research desk in a
> contemporary Indian office, hands reviewing an unbranded company report,
> natural daylight, restrained neutral and deep-green palette, realistic
> editorial cinematography, no logos, no legible numbers, no trading-floor
> imagery, vertical 9:16.

---

## Reel 3 — What quantitative really means

**Cover:** Do all your stocks face the same test?

**Frame:** A quantitative portfolio replaces a fresh opinion on every stock
with the same written rule applied to all of them.

**Runtime:** 205 words · approximately 76 seconds spoken · 82 seconds edited

**Quality gate:** 35/40, pass

### Approved spoken script

**HOOK**

> Look at two stocks you own. One came from your own research and the other from
> a friend's tip, so it is easy to judge each one by a different story. A
> quantitative portfolio refuses to do that.

**BODY 1**

> Quantitative simply means the decisions are written as measurements before a
> particular stock appears. The portfolio follows a process you can inspect and
> repeat.

**BODY 2**

> The rule gives neither story special treatment. It measures both stocks over
> the same period, compares them with the same peer group, and ranks them by the
> same written test before either one can qualify.

**BODY 3**

> On the next review date, the same calculation runs again. A company name
> cannot argue with the rule, and neither can today's headline. The output is a
> ranked list. It offers no target price and no promise about where one stock
> must go next.

**BODY 4**

> Consistency alone does not make a strategy good. A weak rule can also be
> followed perfectly, which is why the idea needs research and testing,
> including a clear account of where it fails.

**TAKEAWAY**

> So, do the stocks in your own portfolio face one written test, or does every
> name get a different story?

**CTA**

> We run four momentum-based portfolios. You can see them at marketworks.in.

### Storyboard

| # | Time | Layout and cut | Spoken cue | Picture, overlay and motion | Build |
|---|---|---|---|---|---|
| 1 | `00:00–00:13` | `TH` → `STACK` | “Look at two stocks you own…” | Two neutral stock cards enter below the speaker: `Your research` and `Friend's tip`. Different story bubbles collect under each, then clear on “refuses.” | Premiere + AE |
| 2 | `00:13–00:25` | `TH` → `GC` | “Quantitative simply means…” | Define the word on camera. Then show a blank rule card being written before either stock card enters. Overlay: `Measurements written before the stock appears.` | AE + Remotion |
| 3 | `00:25–00:45` | `GC` persistent canvas | “The rule gives neither story special treatment…” | Move both cards through the same three fixed zones: `Same period` → `Same peer group` → `Same written test`, ending at a neutral qualification gate. | Remotion |
| 4 | `00:45–01:01` | `STACK` → `GC` | “On the next review date…” | Speaker above a calendar marker. Cut to the same canvas rerunning with updated positions. A headline card knocks against the edge but cannot alter the rule path. | AE + Remotion |
| 5 | `01:01–01:12` | `GC` → `TH` | “The output is a ranked list…” | Ranked cards appear without a forecast arrow. Phrases land one at a time: `Ranked list` · `No target price` · `No promise`. | Remotion + Premiere |
| 6 | `01:12–01:19` | `TH`, tighter | “Consistency alone does not make…” | A plain rule card gains a small question mark. Caption: `A weak rule can be followed perfectly.` | Premiere + AE |
| 7 | `01:19–01:22` | `TH` → end card | Takeaway + CTA | Hold the portfolio question. End card: `One written test?` followed by the wordmark and `marketworks.in`. | Premiere |

**Asset call:** No AI b-roll. The identical path followed by both stock cards is
the visual thesis. Do not reuse the four-decision counter from the earlier
`momentum_rules_reel`.

---

## Reel 4 — Momentum has no permanent favourites

**Cover:** What makes a momentum stock leave?

**Frame:** A momentum portfolio has no permanent favourites; a leader stays
only while it remains among the strongest stocks.

**Runtime:** 213 words · approximately 79 seconds spoken · 88 seconds edited

**Quality gate:** 39/40, pass

### Approved spoken script

**HOOK**

> Once a stock enters your portfolio, it becomes surprisingly easy to find
> reasons for it to stay. Momentum gives that decision a review date.

**BODY 1**

> On the next scheduled review, the portfolio measures every eligible stock
> again and rebuilds the ranking using the latest price history. This process is
> called rebalancing, which simply means bringing the portfolio back to its
> written rules.

**BODY 2**

> A small fall does not automatically remove a stock. If it still ranks among
> the stronger names, it can remain in the basket. When its strength fades
> beyond the strategy's exit rule, it leaves and a stronger name can take its
> place.

**BODY 3**

> The difficult part is emotional. The company can still sound good, and its
> old success can still feel convincing. A momentum portfolio returns to the
> narrower question that brought the stock in: does the original evidence still
> exist?

**BODY 4**

> That rule will make mistakes. A stock can leave and recover soon after. The
> method aims for consistency across many decisions, knowing that no rule finds
> a perfect exit for every company.

**TAKEAWAY**

> So if a stock entered because it was strong, what happens when that strength
> disappears? In a rules-based portfolio, the exit rule was already written
> when the stock entered.

**CTA**

> We run four momentum-based portfolios. You can see them at marketworks.in.

### Storyboard

| # | Time | Layout and cut | Spoken cue | Picture, overlay and motion | Build |
|---|---|---|---|---|---|
| 1 | `00:00–00:11` | `TH` → `STACK` | “Once a stock enters your portfolio…” | One stock card accumulates quiet `reason to stay` notes below the speaker. A calendar marker clears the notes on “review date.” | Premiere + AE |
| 2 | `00:11–00:28` | `GC` ranked-list canvas | “On the next scheduled review…” | A date marker activates; every eligible card is measured again and the ranking rebuilds. Overlay: `Rebalancing = bringing the portfolio back to its written rules.` | Remotion |
| 3 | `00:28–00:47` | `STACK` → `GC` | “A small fall does not automatically…” | A card dips but remains inside the qualifying band. Later its rank falls beyond the exit boundary and a stronger card replaces it. Labels: `Still strong: stays` and `Beyond the exit rule: leaves`. | Remotion + Premiere |
| 4 | `00:47–01:04` | `TH` → `STACK` | “The difficult part is emotional…” | The `reason to stay` notes return faintly. On the final question, every note clears except: `Does the original evidence still exist?` | Premiere + AE |
| 5 | `01:04–01:15` | `TH` → `GC` | “That rule will make mistakes…” | Show a stock card leave the basket and later move upward outside it. Overlay: `A stock can leave and recover.` No regret or crash treatment. | Premiere + Remotion |
| 6 | `01:15–01:24` | `TH` | “The method aims for consistency…” | A sequence of neutral decision cards passes beneath the frame, emphasizing many decisions rather than one perfect exit. | Premiere + AE |
| 7 | `01:24–01:28` | `TH` → end card | Takeaway + CTA | End card: `The exit rule was written when the stock entered.` Then the wordmark and `marketworks.in`. | Premiere |

**Asset call:** No AI b-roll. Keep the emotional recognition on the speaker and
build the ranking mechanism in Remotion.

---

## Reel 5 — When momentum gets caught late

**Cover:** When can momentum look most broken?

**Frame:** Momentum struggles most when the market reverses fast enough to turn
yesterday's weakest stocks into today's leaders.

**Runtime:** 208 words · approximately 77 seconds spoken · 84 seconds edited

**Quality gate:** 36/40, pass

### Approved spoken script

**HOOK**

> Imagine the weak stocks you passed over suddenly rising faster than the
> leaders in your portfolio. That is the moment momentum can look most broken.

**BODY 1**

> Imagine the market has been falling. A momentum portfolio will usually
> contain the stocks that held up better and avoid many of the names that fell
> hardest. Then the market rebounds sharply, and those beaten-down stocks race
> upward while the old leaders pause.

**BODY 2**

> The ranking can flip faster than the portfolio can adjust. It is looking at
> recent price strength by design, so it has to wait until the new leadership
> appears in the data. Researchers call the severe losses that can follow this
> kind of reversal a momentum crash. Past winners fall behind while past losers
> surge.

**BODY 3**

> Portfolio rules can shape this risk. A basket spreads exposure, and position
> limits keep one company from becoming too large. Some systems also reduce
> exposure when the broad market weakens. These controls cannot make a sudden
> reversal disappear.

**TAKEAWAY**

> So when yesterday's weakest stocks suddenly become the new leaders, a
> momentum portfolio can be late to the turn. You can know that failure mode in
> advance, even though you cannot know when it will arrive.

**CTA**

> We run four momentum-based portfolios. You can see them at marketworks.in.

### Storyboard

| # | Time | Layout and cut | Spoken cue | Picture, overlay and motion | Build |
|---|---|---|---|---|---|
| 1 | `00:00–00:11` | `TH` → `STACK` | “the weak stocks you passed over…” | Lower canvas holds `Passed over` and `Portfolio leaders`. The passed-over cards begin rising faster. Overlay: `When the old losers become the new leaders.` | Premiere + Remotion |
| 2 | `00:11–00:31` | `GC` two-group canvas | “Imagine the market has been falling…” | Both groups move down, but leaders fall less. On the rebound, the formerly weak group changes direction sharply and crosses the old leaders. Calm geometry only. | Remotion |
| 3 | `00:31–00:51` | `STACK` → `GC` | “The ranking can flip faster…” | The rank table initially reflects the previous order. It reorders only after the new leaders enter the measured window. Overlay: `The ranking reacts after prices move.` | Remotion + Premiere |
| 4 | `00:51–01:05` | `TH` → `GC` | “Researchers call the severe losses…” | Define the term on camera. Then cross the groups again with: `Past winners fall behind` and `Past losers surge`. Card: `Momentum crash = severe losses during this reversal.` | Premiere + Remotion |
| 5 | `01:05–01:14` | `STACK`, speaker above | “Portfolio rules can shape this risk…” | Build three quiet controls: `Basket` · `Position limits` · `Broad-market exposure rule`. Keep them secondary to the crossing graphic. | AE |
| 6 | `01:14–01:21` | `TH`, tighter | “These controls cannot…” | Remove all graphics. Phrase caption: `cannot make the reversal disappear`. | Premiere |
| 7 | `01:21–01:24` | `TH` → end card | Takeaway + CTA | Freeze the crossing groups faintly behind the speaker. End card: `You can know the failure mode, not when it will arrive.` Then the wordmark and `marketworks.in`. | Premiere + AE |

**Asset call:** No AI b-roll. The restrained rank inversion is clearer and less
sensational than generated market footage.

---

## Production handoff

### Premiere Pro

- Assemble the talking-head edit, apply the fixed-desk crop variants, mix
  dialogue and music, and create the phrase-at-a-time captions.
- Use hard cuts for mechanism changes. Avoid a transition effect on every cut.
- Hold the caveats and final questions on the speaker.

### After Effects

- Build the reusable vertical-stack shell, emphasis marks, calendar marker,
  stock/story cards and end cards.
- Export overlays with alpha when they must sit above the speaker.

### Remotion

- Build reusable components for `MeasuredPricePath`, `PeerComparison`,
  `InformationRipple`, `SameTestPipeline`, `RankedBasket` and `RankInversion`.
- All conceptual charts should be driven by simple illustrative coordinates,
  not fabricated market returns.
- Render full-screen canvases as ProRes; use alpha only for stacked overlays.

### Audio

- One restrained bed across the series.
- Soft ticks for rule-card or rank changes; no casino sounds, impact booms, or
  whooshes on routine transitions.

## Source foundation

The scripts intentionally avoid specific performance figures. Their conceptual
foundation comes from:

- Jegadeesh and Titman's foundational momentum research.
- Hong, Lim and Stein's work on
  [gradual information diffusion](https://www.nber.org/papers/w6553).
- Daniel and Moskowitz on
  [momentum crashes](https://www.nber.org/papers/w20439).
- The official
  [Nifty200 Momentum 30 methodology](https://www.niftyindices.com/indices/equity/strategy-indices/nifty200-momentum-30)
  as an Indian example of a published rules-based momentum process.

## Architecture run: better or worse?

| Dimension | Original draft | Content OS version | Judgment |
|---|---|---|---|
| Frame discipline | Several reels mix the definition, process and broader case | Each reel owns one approved mechanism | **Better** |
| Audience fit | Mostly generic investor language | Hooks repeatedly begin with stocks Karan owns, researched or passed over | **Better** |
| Series differentiation | Reel 1 and Reel 3 repeat parts of the same rank-and-basket process | Reel 1 owns observable strength; Reel 3 owns equal treatment by one written rule | **Better** |
| Risk explanation | Reel 5 lists reversals, costs, taxes, regime rules and backtest risk | Reel 5 explains one failure mechanism: former losers become new leaders faster than the ranking adjusts | **Better** |
| Evidence control | Includes a plausible but unsourced institution-building example | Removes unsupported specifics and keeps claims inside the research dossier | **Better** |
| Runtime accuracy | 170–184 words, roughly 63–68 seconds at the repo convention despite longer labels | 197–213 words, roughly 73–79 seconds spoken, with 78–88 second edit plans | **Better** |
| Visual completeness | Detailed storyboards only for Reels 1 and 2 | Production storyboards for all five reels | **Better** |
| Commercial pressure | No spoken CTAs | Follow CTA on Reels 1–2 and portfolio CTA on Reels 3–5 | **Mixed** — better for conversion, less purely editorial |
| Writing texture | Slightly looser and more spontaneous | More precise, but occasionally more deliberate and framework-shaped | **Mixed** |
| Operational simplicity | One Markdown file | Five packs, dossier, frames, ContentObjects, verdicts, founder files and storyboards | **Worse for speed; better for traceability** |
| Tooling coherence | No harness dependency | The run exposed a legacy voice-guard requirement in `assemble_kit.py`; the assembler was migrated to the v4 quality gate and now packages the storyboard | **Fixed in this run** |

### Overall verdict

The Content OS version is better for this series. Its largest gain is not
wordsmithing; it is separation. Each reel makes one clear promise, teaches one
mechanism, and hands the next reel a clean opening. Reel 4 is the strongest
piece because the emotional problem and the portfolio rule are the same story.

The costs are real. The process is much heavier, the scripts can feel more
constructed, and three product CTAs may be too commercial if the primary goal
is audience trust. A lighter operating version should keep the dossier, one
frame per reel, Karan anchoring, humanizer and independent review while
reducing file ceremony. The kit assembler mismatch found during this run has
been fixed and covered by tests.
