# Curriculum blueprint — Marketworks Market State Lab

Working promise:

> Read the Indian market with evidence, understand how a quant turns ideas into
> rules, and build a local daily dashboard with Codex or Claude Code.

## Course-level outcomes

At completion, a learner can:

1. write a dated description of Indian equity-market state using trend,
   breadth, volatility/stress, concentration, and leadership;
2. explain why an index move and broad-market participation can tell different
   stories;
3. distinguish a market narrative, metric, signal, screen, rule, backtest, and
   forecast;
4. calculate and interpret sector and stock relative strength against a stated
   benchmark without confusing relative strength with RSI;
5. apply three transparent pattern definitions and document their false-positive
   risks; and
6. use Codex or Claude Code to build, test, and operate a local market-state
   dashboard with visible data freshness and an “observation, not
   recommendation” boundary.

## Three-day sequence

| Day | Module | Central question | Learner artifact |
|---|---|---|---|
| 1 | 1. What state is the market in? | What does “the market is up” hide? | Market-state question map |
| 1 | 2. Read trend, breadth, and stress | Is the move broad, healthy, and supported? | Five-line market-state note |
| 2 | 3. Think like a quant | How does an idea become a transparent measurement? | Signal anatomy card |
| 2 | 4. Find leadership and patterns | Who is leading, and what price events are observable? | Pattern definition sheet + shortlist |
| 3 | 5. Build the local dashboard with AI | Can the frozen definitions be reproduced on-device? | Running dashboard |
| 3 | 6. Audit it and create a daily habit | Can the learner trust, explain, and update the output? | Dashboard audit + ten-minute routine |

Each module is approximately 60 minutes:

- 15 minutes — concept in plain English;
- 15 minutes — annotated Marketworks walkthrough;
- 20 minutes — individual mission; and
- 10 minutes — concept check, explanation, and debrief.

## Day 1 — Read the market, not the headline

### Module 1 — What state is the market in?

**Question:** What does a Nifty headline tell you, and what does it leave out?

#### Concepts

1. “Market state” is a dated description, not a prediction.
2. Index, benchmark, and investable universe are different objects.
3. Price direction, participation, leadership, volatility, and drawdown answer
   different questions.
4. Market state can be mixed; one indicator does not need to win.
5. Observation, inference, implication, and instruction must stay separate.

#### Marketworks walkthrough

Open the current Pulse or equivalent market overview and identify:

- the as-of date;
- the broad index direction and trend reference;
- the stated market regime;
- the breadth reading;
- the stress/volatility context; and
- one thing the page does not establish.

#### Mission — market-state question map

For a supplied headline such as “Nifty closes at a record high,” write the next
five questions:

1. Is the index above its medium/long-term trend?
2. How many stocks are participating?
3. Is leadership broad or concentrated?
4. Which sectors are leading?
5. Is volatility/stress confirming or contradicting the move?

#### Check for understanding

The learner must reject:

- “Nifty rose, therefore most stocks rose.”
- “A bull regime means the market will rise tomorrow.”
- “A strong market means every breakout is valid.”

### Module 2 — Read trend, breadth, and stress

**Question:** Is the current move broad, healthy, and supported?

#### Concepts

1. Trend: close relative to a stated moving average.
2. Breadth level: percentage of an NSE 500-like universe above the 50-DMA and
   200-DMA.
3. Breadth momentum: advances versus declines or one simple breadth oscillator.
4. Drawdown and extension: distance from a recent peak and from trend.
5. Volatility/stress as context, not a direction forecast.
6. Concentration: an index can rise while participation narrows.
7. Direction matters: 60% breadth rising from 40% differs from 60% falling from
   80%.

#### Marketworks walkthrough

Use the breadth history, stress/regime, and concentration views to answer:

- Is long-term participation above or below half the universe?
- Is breadth improving or deteriorating?
- Is the market trend broad or dependent on a few names?
- Is the current reading calm, stretched, drifting, or stressed?
- What is the data date and coverage?

#### Mission — five-line market-state note

Write exactly five dated lines:

1. **Direction:** broad index relative to trend.
2. **Participation:** breadth level and direction.
3. **Leadership:** leading sectors and whether leadership is broad.
4. **Risk context:** volatility, stress, drawdown, or extension.
5. **Uncertainty:** one contradiction or missing input.

No line may contain “buy,” “sell,” “target,” “must,” or “will.”

#### Check for understanding

Given three market snapshots, choose the most defensible description and mark
each sentence as observation, inference, or unsupported claim.

## Day 2 — Turn a market idea into a quant rule

### Module 3 — Think like a quant

**Question:** How does a useful idea become a transparent measurement?

#### Concepts

1. The quant chain:
   **question → universe → data → metric → comparison → screen → review**.
2. A metric describes; a signal transforms; a screen filters; a rule specifies
   an action; a backtest studies historical behavior; a forecast claims
   something about the future.
3. Universe and benchmark choice change the answer.
4. Lookbacks are design choices, not natural laws.
5. No future-data access: values must use information available as of the
   displayed date.
6. Missing data, survivorship, corporate actions, and stale prices can create
   clean but wrong outputs.
7. Reproducibility beats complexity.

#### Marketworks walkthrough

Reverse-engineer three existing readings:

- `% above 200-DMA`;
- six-month relative strength versus Nifty 50; and
- a 20-day breakout.

For each, identify universe, input, lookback, comparison, output, and one
failure mode.

#### Mission — signal anatomy card

Freeze one metric in plain language:

```text
Question:
Universe:
Input columns:
As-of rule:
Lookback:
Calculation:
Benchmark/comparison:
Output:
What it describes:
What it does not prove:
Known failure modes:
```

#### Check for understanding

Learners diagnose:

- relative strength versus RSI;
- today’s close compared with a high that accidentally includes today;
- a breadth calculation that silently drops half the universe; and
- a screen described as a forecast.

### Module 4 — Find leadership and price patterns

**Question:** Who is leading, and which observable price events deserve a
closer look?

#### Concepts

1. Sector relative strength: sector return minus Nifty 50 return over a stated
   window.
2. Stock relative strength: stock return minus benchmark return over 126
   trading days.
3. RS level versus RS direction and leadership tenure.
4. Why a one-day gap can create misleading relative strength.
5. Breakout level, closing confirmation, trend context, volume context, and
   extension risk.
6. Pattern matches are observation lists, not entries.

#### Three pattern definitions

1. **Fresh 20-day breakout**
   - close today is above the highest close of the previous 20 sessions;
   - the previous-high window excludes today; and
   - close is above the 50-DMA.

2. **Fresh 52-week breakout**
   - close today is above the highest close of the previous 252 sessions;
   - the previous-high window excludes today; and
   - close is above the 50-DMA.
   - This is descriptive only; the course makes no forward-return claim.

3. **Coiled spring / pre-breakout watch**
   - close is above the 50-DMA and 200-DMA;
   - 20-day realized volatility is below the stock’s own historical first
     quartile; and
   - it is explicitly labeled a setup, not a breakout.

Every candidate also shows:

- as-of date;
- sector;
- 126-day RS versus Nifty 50;
- distance from the relevant level;
- distance from 50-DMA and 200-DMA;
- volume ratio when trustworthy volume data is available;
- data-quality/coverage flag; and
- a reason the match may fail.

#### Marketworks walkthrough

Compare the sector, RS leader, breakout, coiled-spring, extension, and stock
detail views. Find one example where:

- a strong stock sits in a weak sector;
- a breakout appears in weak breadth; or
- an RS leader is too extended to call “early.”

#### Mission — observation shortlist

Select one candidate from each pattern list and write:

- the exact rule it matched;
- market and sector context;
- one confirming observation;
- one contradiction;
- the level or condition that would invalidate the pattern description; and
- what additional fundamental research would still be required.

The artifact title must say **observation shortlist**, never “stock picks.”

## Day 3 — Build and own the dashboard

### Module 5 — Build the local dashboard with AI

**Question:** Can Codex or Claude Code reproduce the frozen definitions on the
learner’s device?

#### Concepts

1. AI coding agent versus AI market oracle.
2. Starter folder, data dictionary, environment, permissions, and test loop.
3. Why `METRICS.md` is frozen before implementation.
4. Separating data preparation, calculations, presentation, and commentary.
5. A dashboard is only as current and complete as its inputs.

#### Mission

Complete prompts 1-5 in `AI_MARKET_DASHBOARD_LAB.md`:

- inspect the starter kit;
- freeze `METRICS.md`;
- plan the build;
- implement the local dashboard;
- run tests and reconcile one sample calculation manually.

Required dashboard panels:

1. data date, universe, benchmark, and coverage;
2. broad trend, drawdown, and volatility context;
3. breadth above 50-DMA and 200-DMA;
4. sector breadth and relative-strength table;
5. stock relative-strength leaders; and
6. the three pattern observation lists.

No learner needs to write code from scratch. They must be able to explain what
the agent built and locate the metric definitions.

### Module 6 — Audit it and create a daily habit

**Question:** Can the learner trust, explain, and update the dashboard?

#### Concepts

1. Data freshness, incomplete sessions, missing symbols, adjusted prices, and
   universe drift.
2. Calculation tests versus visual checks.
3. False precision and unsupported natural-language summaries.
4. Pattern false positives in narrow, stressed, or extended markets.
5. Versioning definitions before changing them.
6. Comparing a local educational build with a production research platform.

#### Mission — dashboard audit

Complete the required checks in `AI_MARKET_DASHBOARD_LAB.md`, then ask the agent to
produce:

- a one-page `DASHBOARD_AUDIT.md`;
- a plain-language data freshness banner;
- a visible “observation, not recommendation” label;
- a five-line daily note generated only from displayed metrics; and
- a `RUN_DAILY.md` guide.

#### Ten-minute operating routine

1. **Minute 0-1:** confirm data date and coverage.
2. **Minute 1-3:** read broad trend, drawdown, and stress.
3. **Minute 3-5:** read breadth level and direction.
4. **Minute 5-7:** identify leading and weakening sectors.
5. **Minute 7-9:** inspect pattern lists in market context.
6. **Minute 9-10:** write one observation, one contradiction, and one question.

The learner then compares the local note with the equivalent Marketworks views:

- Which readings agree?
- Which differ because of universe, benchmark, date, or methodology?
- What does Marketworks calculate that the local build does not?
- Which output would be unsafe to treat as an instruction?

## Assessment design

### Module artifact rubric

Score each artifact 0-2 on:

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Definition | Missing/wrong | Partly correct | Correct and plain-language |
| Evidence | Unsupported | Some dated evidence | Dated, sourced, reproducible |
| Separation | Advice/prediction | Mixed categories | Observation/inference clearly separated |
| Limitations | None | Generic caveat | Specific failure mode or contradiction |
| Independence | Cannot explain | Explains with help | Explains and reproduces one calculation |

### Completion standard

- all six modules attempted;
- at least five of six artifacts complete;
- dashboard runs locally from the documented command;
- freshness, coverage, and educational-purpose labels visible;
- one calculation manually reconciled;
- dashboard audit complete; and
- no broker connection, personal portfolio data, or trade instruction.

Completion does not depend on finding a “successful” pattern or forming a
bullish/bearish view.
