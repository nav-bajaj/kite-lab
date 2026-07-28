# Curriculum blueprint — Marketworks Market State Lab

Status: detailed learning-design draft. The AI implementation sequence remains
the next design pass.

Working promise:

> Read the Indian market with evidence, understand how a quant turns ideas and
> chart shapes into rules, and build a local daily dashboard you can inspect.

## Course shape

- **Audience:** Indian investor aged 22-28 with mutual-fund experience, some
  stock awareness, and basic AI-chat familiarity.
- **Duration:** three days, two 60-minute modules per day.
- **Total instructional time:** six hours.
- **Delivery:** live cohort or tightly facilitated self-paced pilot.
- **Primary practice surface:** current Marketworks Insights and Learn views.
- **Capstone:** local market-state and pattern-observation dashboard.
- **Promise:** better market-reading and measurement, not trading performance.

## Course-level outcomes

At completion, a learner can:

1. **Define and describe the market.** Explain the Indian listed-equity funnel,
   justify the course's dated Nifty 500-derived universe, and write a dated
   market-state description without turning it into a prediction.
2. **Read beneath an index.** Explain why index direction and broad-market
   breadth may disagree, and identify what the index headline leaves unknown.
3. **Think quantitatively.** Convert a narrative into a versioned metric or
   screen with a universe, input data, lookback, comparison, output, and
   failure case.
4. **Read leadership and structure.** Calculate relative strength, distinguish
   it from RSI, interpret simple price landmarks, and inspect three
   quantitatively detected chart-pattern families.
5. **Build with AI while retaining ownership.** Use Codex or Claude Code to
   reproduce frozen definitions locally and explain the calculation and chart
   behind each output.
6. **Audit and maintain the result.** Check freshness, coverage, look-ahead,
   corporate actions, visual/numeric agreement, and unsupported commentary,
   then follow a ten-minute daily routine.

## Evidence of learning

The learner leaves with six artifacts:

| Module | Artifact | What it proves |
|---|---|---|
| 1 | Indian equity universe map + decision card | Can define which market is being measured and why |
| 2 | Five-line market-state note | Can synthesize dated, conflicting evidence |
| 3 | Signal anatomy card | Can turn an intuition into a reproducible definition |
| 4 | Pattern criteria sheet + observation shortlist | Can reconcile quantitative detection with a visual overlay |
| 5 | Running local dashboard + explanation card | Can operate and explain an AI-assisted build |
| 6 | Dashboard audit + ten-minute routine | Can challenge, update, and use the output responsibly |

## Three-day sequence

| Day | Module | Central question | Main transition |
|---|---|---|---|
| 1 | 1. Define the market before reading it | Which stocks do we mean by “the market”? | Listed landscape → dated universe |
| 1 | 2. Read trend, breadth, and stress | Is the move broad and internally supported? | Indicators → dated synthesis |
| 2 | 3. Think like a quant | How does an idea become a transparent measurement? | Intuition → specification |
| 2 | 4. Find leadership and chart structures | Can a visual shape be detected reproducibly? | Eyeballing → geometry + overlay |
| 3 | 5. Build the local dashboard with AI | Can frozen definitions be reproduced on-device? | Specification → working tool |
| 3 | 6. Audit it and create a daily habit | Can the learner trust and maintain the output? | Tool → owned process |

## Course language contract

The following distinctions are taught and enforced throughout:

| Term | Course meaning |
|---|---|
| Observation | A dated value or shape calculated from available data |
| Inference | A tentative interpretation of one or more observations |
| Metric | A defined measurement |
| Signal | A transformation of data intended to mark a condition or event |
| Screen | A rule that filters a stated universe |
| Pattern | A versioned geometric relationship among price observations |
| Forecast | A claim about a future outcome |
| Instruction | A recommended action for a person |

A pattern match is an observation. It is not automatically a forecast or an
instruction.

# Day 1 — Read the market, not the headline

## Module 1 — Define the market before reading it

**Central question:** Which stocks do we mean by “the Indian market,” and why
does Marketworks begin with a dated Nifty 500-derived universe?

The complete authored pack is in `modules/01_market_universe/`.

### Learner can

By the end of the hour, the learner can:

- distinguish a company, security, exchange, listing, index, and research
  universe;
- map the funnel from India's overlapping exchange-listed landscape to
  eligible common equity;
- explain the Nifty 500's large-, mid-, and small-cap construction;
- justify the Nifty 500 as a practical first learning/research universe without
  calling every constituent suitable to own;
- distinguish free-float index weighting from equal-stock breadth counting; and
- state the universe date, active denominator, and material exclusions.

### Core vocabulary

Company, security, listing, exchange, main board, SME, index, constituent,
research universe, eligibility, market capitalization, free float, liquidity,
impact cost, breadth, membership date, coverage.

### 60-minute lesson plan

| Time | Activity | Instructor/product role |
|---|---|---|
| 0-5 | Hook: “How many stocks are in the Indian market?” | Collect 50, 500, 750, 2,000+, and uncertain answers |
| 5-13 | Five different objects | Sort company, security, exchange, index, and universe |
| 13-22 | Indian-market funnel | Map exchanges/products to eligible common equity |
| 22-32 | Nifty 500 construction | Explain eligibility, size ladder, weighting, and review |
| 32-42 | Marketworks walkthrough | Locate official index, dated universe, metric denominator, and exclusions |
| 42-50 | Weighted index versus breadth | Calculate the ten-stock divergence fixture |
| 50-56 | Individual mission | Complete the universe map and decision card |
| 56-60 | Quiz and exit ticket | Require the index-versus-breadth question |

### Concept model — the universe funnel

```text
India's exchange-listed landscape
→ NSE-listed companies and multiple security types
→ eligible, traded common equity
→ official Nifty 500
→ Marketworks dated constituent and data-coverage snapshot
```

The official Nifty 500 contains the large-cap 100, mid-cap 150, and small-cap
250 layers under the current index framework. The course explains that it
covers most, not all, of the NSE market and does not include the full microcap
and listed tail.

### Marketworks walkthrough

The instructor moves between:

1. the official Nifty 500 definition and methodology;
2. the Marketworks Pulse page;
3. `% above 200-DMA` Learn content; and
4. the screener.

The learner completes:

```text
Official index:
Product universe:
Membership/snapshot date:
Index weighting:
Breadth counting method:
Intended members:
Metric-eligible members:
Missing/excluded:
```

### Mission — Indian equity universe map + decision card

The learner draws the funnel and then states:

- the market question;
- official reference universe;
- product snapshot and date;
- eligibility logic;
- size coverage;
- weighting versus counting method;
- three reasons the universe fits; and
- at least three blind spots.

### Mastery evidence

The artifact passes when:

- NSE/BSE counts are not added as disjoint companies;
- index and exchange are not treated as synonyms;
- the official Nifty 500 name is distinguished from product shorthand;
- the learner explains both broad coverage and excluded tail;
- index weighting and breadth counting are distinguished;
- membership date and active denominator are visible; and
- index inclusion is not presented as quality certification or advice.

### Misconceptions to surface

- “The Nifty 500 is every stock on NSE.”
- “These are the 500 safest Indian stocks.”
- “A broker search is a research universe.”
- “The company with the highest share price is the largest.”
- “If the index is positive, most constituents must be positive.”
- “Exactly 500 stocks have usable history on every date.”

### Instructor preparation

- five-object card set;
- exchange-overlap diagram;
- Indian equity-universe funnel;
- Nifty 500 eligibility and size-ladder visual;
- ten-stock weighted-index/breadth fixture;
- dated Marketworks universe contract; and
- current official sources and product screenshots.

## Module 2 — Read trend, breadth, and stress

**Central question:** Is the current move broad and internally supported?

### Learner can

By the end of the hour, the learner can:

- interpret price relative to a stated moving average;
- calculate percentage-above-DMA breadth on a small universe;
- distinguish breadth level from breadth direction;
- use drawdown and volatility as context rather than prediction; and
- write a five-line state note with one explicit contradiction.

### Core vocabulary

Moving average, breadth, denominator, coverage, advance, decline,
concentration, drawdown, realized volatility, extension, contradiction.

### 60-minute lesson plan

| Time | Activity | Instructor/product role |
|---|---|---|
| 0-6 | Retrieval from Module 1 | Rebuild the five-layer stack from memory |
| 6-15 | Trend and drawdown | Demonstrate one index above 50-DMA but below prior peak |
| 15-26 | Breadth by hand | Calculate `% above 200-DMA` for a ten-stock fixture |
| 26-33 | Level versus direction | Compare 60% rising from 40% with 60% falling from 80% |
| 33-43 | Marketworks walkthrough | Read breadth history, concentration, and stress together |
| 43-55 | Individual mission | Write the five-line note |
| 55-60 | Concept check | Identify observation, inference, and unsupported claim |

### Calculation fixture

The ten-stock worksheet includes:

- symbol;
- current adjusted close;
- 50-DMA and 200-DMA;
- prior-session close;
- sector; and
- one missing 200-DMA value.

The learner must show both numerator and denominator. The missing value is not
silently counted as below the moving average.

### Marketworks walkthrough script

Use breadth history, regime/stress, and concentration views to answer:

- Is the broad index above medium- and long-term trend?
- What percentage of the covered universe is above 50-DMA and 200-DMA?
- Is participation improving or deteriorating?
- Is the index move concentrated in a small number of large constituents?
- Are drawdown, volatility, and extension telling the same story?
- What is the denominator and data coverage?

### Mission — five-line market-state note

Write exactly five dated lines:

1. **Direction:** benchmark relative to stated trend references.
2. **Participation:** breadth level, direction, and denominator.
3. **Leadership:** leading sectors and whether leadership is broad.
4. **Risk context:** drawdown, volatility, stress, or extension.
5. **Contradiction:** one reason the evidence does not support a simple label.

No line may contain “buy,” “sell,” “target,” “must,” “will,” or “safe.”

### Mastery evidence

The note passes when:

- it contains an as-of date;
- every factual claim maps to a visible field;
- breadth includes its universe or denominator;
- one contradiction is specific rather than a generic disclaimer; and
- no descriptive metric becomes an implied market call.

### Misconceptions to surface

- A moving average is an intrinsic fair-value estimate.
- Breadth above 50% is always healthy.
- Low volatility means low risk.
- A strong index invalidates weak breadth.
- Missing symbols belong in the denominator.

### Instructor preparation

- ten-stock breadth fixture and answer key;
- paired breadth-history charts with the same endpoint and different paths;
- narrow-index-rally example; and
- one stale-data example.

# Day 2 — Turn intuition and chart shapes into rules

## Module 3 — Think like a quant

**Central question:** How does a useful idea become a transparent
measurement?

### Learner can

By the end of the hour, the learner can:

- move through the quant chain from question to review;
- distinguish metric, signal, screen, pattern, rule, backtest, and forecast;
- write a data and as-of contract;
- identify one look-ahead error and one coverage error; and
- freeze a metric definition before any code is generated.

### Core vocabulary

Universe, benchmark, field, lookback, threshold, normalization, adjusted
price, survivorship, look-ahead, version, reproducibility, false positive.

### 60-minute lesson plan

| Time | Activity | Instructor/product role |
|---|---|---|
| 0-7 | Narrative teardown | Start with “strong stocks keep getting stronger” |
| 7-16 | Quant chain | Question → universe → data → metric → comparison → screen → review |
| 16-24 | Definitions ladder | Sort metric, signal, screen, pattern, rule, backtest, forecast |
| 24-32 | Data traps | Demonstrate future pivot, split gap, missing denominator, universe drift |
| 32-43 | Marketworks reverse-engineering | Inspect breadth, relative strength, and 20-day breakout |
| 43-55 | Individual mission | Complete a signal anatomy card |
| 55-60 | Debugging check | Diagnose four short flawed definitions |

### Reverse-engineering exercise

For each current Marketworks reading, identify:

| Reading | Universe | Input | Lookback | Comparison | Output | One failure mode |
|---|---|---|---|---|---|---|
| `% above 200-DMA` |  |  |  |  |  |  |
| 126-day relative strength |  |  |  |  |  |  |
| Fresh 20-day breakout |  |  |  |  |  |  |

The learner does not need the production implementation. The goal is to expose
every methodological choice hidden behind a short label.

### Mission — signal anatomy card

```text
Question:
Universe:
Benchmark:
Required input fields:
Adjustment policy:
As-of rule:
Lookback:
Calculation:
Threshold/comparison:
Output:
What it describes:
What it does not prove:
Known failure modes:
Methodology version:
```

### Mastery evidence

The card passes when another learner could implement the same calculation
without asking what the author “meant.”

### Debugging check

Learners diagnose:

1. a 20-day high that includes today's close in the prior-high window;
2. a pivot detector that uses future sessions without delaying the signal;
3. a breadth calculation that silently drops half the universe; and
4. a screen described as a forecast.

### Misconceptions to surface

- More decimal places make a signal more objective.
- A widely used lookback is a natural law.
- A chart drawn from adjusted closes guarantees adjusted highs and lows.
- Backtesting a definition makes it valid.
- AI-generated code removes the need for a written specification.

### Instructor preparation

- one intentionally ambiguous metric prompt;
- four debugging cards;
- split-adjustment illustration;
- small look-ahead example; and
- blank and completed signal anatomy cards.

## Module 4 — Find leadership and quantitative chart structures

**Central question:** Who is leading, and can a visual chart shape be detected
reproducibly?

Detailed geometry lives in `QUANT_PATTERN_SPEC.md`.

### Learner can

By the end of the hour, the learner can:

- calculate simple relative strength versus Nifty 50;
- explain why relative strength is not RSI;
- distinguish a price landmark, condition, and geometric pattern;
- explain confirmed pivots, ATR-normalized tolerance, containment, and
  completed-close breakout;
- inspect a triangle, rectangle, or bull flag criteria matrix; and
- reject a visually persuasive chart when the quantitative definition fails.

### Pattern scope

#### Simple landmarks and conditions

- fresh 20-session closing-high breakout;
- fresh 252-session closing-high breakout; and
- coiled-spring / low-volatility pre-breakout condition.

#### Geometric families

1. converging triangle breakout;
2. rectangle/base breakout; and
3. bull flag breakout.

The module teaches three geometries, not three promises:

- converging boundaries;
- horizontal boundaries; and
- impulse plus controlled pullback.

### 60-minute lesson plan

| Time | Activity | Instructor/product role |
|---|---|---|
| 0-8 | Relative strength calculation | Compare stock and sector returns with Nifty 50 |
| 8-14 | RS versus RSI | Contrast benchmark-relative performance with bounded momentum oscillator |
| 14-21 | Landmarks versus structures | Separate 20-day/52-week highs and coiled spring from geometry |
| 21-31 | Geometry toolkit | Teach confirmed pivots, ATR tolerance, boundaries, containment, close confirmation |
| 31-42 | Three pattern walkthroughs | Show one passing and one rejected overlay per family |
| 42-55 | Individual pattern lab | Reconcile a criteria matrix with an annotated chart |
| 55-60 | Exit check | Explain one rejected visual and one limitation |

### Geometry toolkit

The learner does not calculate a regression by hand. They must understand:

1. **Confirmed pivot:** a local high or low becomes usable only after later
   sessions confirm it.
2. **Tolerance:** price rarely touches an exact line; ATR converts “near” into
   a volatility-aware distance.
3. **Boundary:** a line fitted to confirmed pivots, not a line moved by eye to
   make the chart fit.
4. **Containment:** most observations must remain inside the claimed shape.
5. **Fresh breakout:** completed close crosses the versioned boundary plus a
   visible buffer, while the prior close had not.
6. **Rejection reason:** every near-match explains which criterion failed.

### Quantitative-plus-visual rule

A candidate enters the learner's observation shortlist only when:

- the program's criteria matrix passes;
- the visual uses the same pivots and boundaries as the program;
- the as-of date and methodology version are visible;
- the learner can point to the geometry represented by each diagnostic; and
- the learner records one reason the match may be misleading.

The dashboard displays no composite “pattern quality” or “buy” score.

### Marketworks walkthrough script

Compare sector, RS leader, breakout, coiled-spring, extension, and stock-detail
views. Then open the teaching pattern overlay and ask:

- Is the stock leading its benchmark, and over what window?
- Is this a simple high, a low-volatility condition, or a geometric structure?
- Which pivots created the boundaries?
- Is the latest pivot actually confirmed?
- Which numerical criterion is visible on the chart?
- Did a completed close cross the level?
- What market or sector condition contradicts the setup?

### Mission — pattern criteria sheet + observation shortlist

The learner receives:

- one accepted pattern candidate;
- one visually plausible rejected candidate; and
- one simple landmark or coiled-spring observation.

For each:

```text
Symbol/date:
Observation type:
Exact methodology version:
Rule or geometry matched:
Values that passed:
Values that failed:
What the visual confirms:
What the visual does not establish:
Market/sector context:
Data-quality issue:
One reason to reject or investigate further:
```

The learner may select at most one item for an **observation shortlist**. The
artifact must never be titled “stock picks.”

### Mastery evidence

The artifact passes when:

- relative strength has a stated benchmark and lookback;
- the learner correctly separates RS from RSI;
- every pattern statement maps to a numeric criterion;
- the learner rejects the near-match for the program's stated reason;
- the visual is used to audit the program rather than override it; and
- no match is converted into an entry, target, or expected return.

### Misconceptions to surface

- A familiar-looking triangle is a triangle by definition.
- Drawing more trendlines increases accuracy.
- Touching resistance intraday is a breakout.
- High volume validates every shape.
- Relative strength means the stock is overbought.
- A detector's pass result is equivalent to a forecast.

### Instructor preparation

For each pattern family:

- one synthetic clean pass;
- one near-match with a failed criterion;
- one intraday cross without closing confirmation;
- criteria matrices and answer keys; and
- charts with program-generated pivots and boundaries.

Also prepare one corporate-action distortion and one unconfirmed-pivot example.

# Day 3 — Build and own the dashboard

Day 3 is specified here from the learner's perspective. Agent permissions,
prompt sequence, scaffold, charting library, test fixtures, and recovery paths
will be resolved in the dedicated AI design pass.

## Module 5 — Build the local dashboard with AI

**Central question:** Can Codex or Claude Code reproduce the frozen definitions
on the learner's device?

### Learner can

By the end of the hour, the learner can:

- describe the difference between an AI coding agent and a market oracle;
- inspect the starter folder and data dictionary before permitting changes;
- point the agent to frozen metric and pattern definitions;
- start the local application from a documented command;
- reconcile one displayed value with a reference fixture; and
- explain where the data, calculation, visualization, and commentary live.

### 60-minute lesson plan

| Time | Activity | Instructor/product role |
|---|---|---|
| 0-7 | Safety and ownership briefing | Establish local-only and no-credential boundary |
| 7-15 | Starter-kit tour | Locate data, definitions, tests, app, and run guide |
| 15-23 | Agent plan review | Learner approves a bounded plan before edits |
| 23-38 | Guided build/run | Agent assembles or completes the scaffold |
| 38-47 | Pattern overlay check | Open one detector row and reconcile criteria with chart |
| 47-55 | Manual reference check | Compare one breadth or breakout value with fixture |
| 55-60 | Explanation check | Learner explains the project map without agent help |

### Required dashboard learning interface

1. data date, source, universe, benchmark, and coverage;
2. broad trend, drawdown, and volatility context;
3. breadth above 50-DMA and 200-DMA;
4. sector breadth and relative-strength table;
5. stock relative-strength observations;
6. simple landmark/condition list;
7. three geometric pattern-family lists;
8. drill-down chart with program-generated overlay and criteria matrix; and
9. five-line note workspace.

### Mission — running dashboard + explanation card

The learner:

1. inspects the starter kit;
2. reads the frozen methodology files;
3. reviews the agent's plan;
4. runs the provided build path;
5. opens one pattern candidate;
6. checks that its visual and criteria matrix agree;
7. reconciles one simple calculation; and
8. completes:

```text
How I start the dashboard:
Where the data comes from:
Where metric definitions live:
Where pattern definitions live:
Where tests live:
One value I checked manually:
One pattern overlay I reconciled:
What the agent changed:
What I still cannot verify:
```

### Mastery evidence

- application opens from the documented local command;
- no broker, personal account, or credentials are connected;
- methodology version and as-of date are visible;
- learner locates data, definitions, tests, and chart code;
- one reference value matches; and
- learner explains one pattern row without referring to “AI confidence.”

### Instructor preparation and support boundary

Required before pilot:

- clean macOS and Windows setup paths;
- synthetic reference dataset;
- precomputed answer fixtures;
- predictable no-network fallback;
- reset/recovery instructions;
- one intentionally broken overlay; and
- a facilitator escalation guide.

The technical implementation of these materials is deliberately deferred to
the next AI design pass.

## Module 6 — Audit it and create a daily habit

**Central question:** Can the learner trust, explain, and update the dashboard?

### Learner can

By the end of the hour, the learner can:

- audit freshness, coverage, adjusted-price policy, and methodology version;
- distinguish calculation tests from visual checks;
- find look-ahead in pivot confirmation;
- detect disagreement between pattern diagnostics and chart overlay;
- challenge unsupported natural-language commentary; and
- complete a ten-minute daily market-reading routine.

### 60-minute lesson plan

| Time | Activity | Instructor/product role |
|---|---|---|
| 0-8 | Audit hierarchy | Data → calculation → geometry → presentation → commentary |
| 8-20 | Bug hunt | Learners inspect stale date, missing coverage, split gap, and future pivot |
| 20-30 | Pattern audit | Reconcile criteria matrix, pivots, boundaries, and status |
| 30-39 | Commentary audit | Remove unsupported prediction and false precision |
| 39-51 | Daily routine rehearsal | Run the ten-minute process on a dated snapshot |
| 51-57 | Compare with Marketworks | Explain differences in universe, date, and methodology |
| 57-60 | Final exit check | State what is known, inferred, unknown, and unsafe |

### Audit hierarchy

1. **Data:** Is it current, complete, adjusted, and allowed?
2. **Calculation:** Does a reference fixture reproduce the displayed value?
3. **Geometry:** Do pivots, boundaries, and status use the written definition?
4. **Presentation:** Does the chart show the values the detector used?
5. **Commentary:** Does each sentence trace to a displayed field?

### Bug-hunt fixtures

- stale as-of date with a fresh-looking chart;
- breadth denominator silently reduced by missing histories;
- unadjusted split mistaken for a pattern;
- pivot used before its confirmation delay;
- triangle overlay drawn from pivots different from the criteria matrix;
- intraday boundary cross mislabeled as completed-close breakout; and
- natural-language summary that turns a match into a recommendation.

### Mission — dashboard audit

```text
Data date/source:
Universe and coverage:
Adjustment policy:
Methodology versions:
Reference calculation checked:
Pattern geometry checked:
Visual/numeric agreement:
Look-ahead check:
Unsupported commentary removed:
Known limitations:
Safe to use for:
Not safe to use for:
```

### Ten-minute operating routine

1. **Minute 0-1:** confirm date, source, methodology, and coverage.
2. **Minute 1-3:** read broad trend, drawdown, and stress.
3. **Minute 3-5:** read breadth level and direction.
4. **Minute 5-6:** identify leading and weakening sectors.
5. **Minute 6-8:** inspect landmarks and pattern candidates in context.
6. **Minute 8-9:** open one overlay and its rejection/pass criteria.
7. **Minute 9-10:** write one observation, one contradiction, and one question.

### Comparison with Marketworks

The learner answers:

- Which readings agree?
- Which differ because of universe, benchmark, date, or methodology?
- Which production calculation is intentionally not reproduced locally?
- Does the local detector show a structure that Marketworks does not?
- Which output would be unsafe to treat as an instruction?

### Mastery evidence

- learner finds at least two seeded issues;
- learner catches a visual/numeric pattern disagreement;
- final market note contains no unsupported future claim;
- local/Marketworks differences are explained rather than “resolved” by
  choosing the preferred answer; and
- learner can rerun the routine without instructor prompts.

# Assessment design

## Module artifact rubric

Score each artifact 0-2 on:

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Definition | Missing or wrong | Partly specified | Reproducible and plain-language |
| Evidence | Unsupported | Some dated evidence | Dated, sourced, and traceable |
| Separation | Advice/prediction | Categories mixed | Observation and inference separated |
| Visual/numeric agreement | Not checked | Checked superficially | Same values and geometry reconciled |
| Limitations | None | Generic caveat | Specific failure or contradiction |
| Independence | Cannot explain | Explains with help | Explains and reproduces one check |

Modules 1-3 may mark visual/numeric agreement “not applicable.” Modules 4-6
must score at least 1 on that dimension.

## Final scenario assessment

The learner receives a dated dashboard snapshot containing:

- rising Nifty 50;
- weakening 200-DMA breadth;
- one strong sector;
- one high-RS stock;
- one accepted triangle;
- one rejected bull flag;
- one stale symbol; and
- one sentence that implies a recommendation.

In 12 minutes, the learner must:

1. write the five-line market note;
2. explain the contradiction between index and breadth;
3. define relative strength;
4. identify why the bull flag failed;
5. verify one triangle diagnostic against the overlay;
6. flag the stale symbol; and
7. remove the unsafe sentence.

## Completion standard

- all six modules attempted;
- at least five of six artifacts complete;
- final scenario score at least 70%;
- dashboard runs locally from the documented command;
- freshness, coverage, methodology, and educational-purpose labels visible;
- one calculation manually reconciled;
- one pattern's numeric and visual outputs reconciled;
- dashboard audit complete; and
- no broker connection, personal portfolio data, or trade instruction.

Completion does not depend on finding a “successful” pattern, producing a
bullish/bearish view, or earning a simulated return.

# Curriculum assets to create before AI implementation

1. six instructor scripts using the minute plans above;
2. six learner artifact templates;
3. ten-stock breadth fixture;
4. relative-strength calculation fixture;
5. signal-anatomy debugging cards;
6. three clean geometric pattern fixtures;
7. at least three rejected/near-match pattern fixtures;
8. program-generated annotated charts and criteria matrices;
9. final scenario assessment and answer key; and
10. pattern-threshold usability findings from five learners.

The dedicated AI pass should begin only after the pattern fixtures and learner
language are stable. Otherwise, the implementation will harden definitions the
course has not yet validated.
