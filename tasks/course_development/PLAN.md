# course_development — market-state intensive

Opened 2026-07-28 on branch `course-development`.

## Executive recommendation

Build and pilot **Marketworks Market State Lab: Read the Market. Build Your
Dashboard.**, a three-day, six-module, six-hour intensive for curious Indian
investors aged 22-28.

This is a deliberate pivot away from a broad four-week foundations course.
Instead of trying to cover the entire product shelf, capital-market plumbing,
stock research, portfolio construction, and backtesting, the course teaches one
coherent job:

> By the end, you can describe the state of the Indian equity market with
> dated evidence, explain the basic logic of quantitative investing, and run a
> local daily dashboard that tracks breadth, trend, leadership, relative
> strength, simple price landmarks, and quantitatively detected chart
> structures with inspectable visual overlays.

The promise is a repeatable observation process, not a forecast or a list of
stocks to buy.

## Why the tighter concept is stronger

1. **It has one clear transformation.** The learner moves from reading index
   headlines to reading participation, trend, volatility, and leadership.
2. **It is native to Marketworks.** Market regime, breadth, stress, sector
   leadership, relative strength, and watchlists are already live product
   surfaces.
3. **Six hours is enough to finish something useful.** A local dashboard is a
   credible capstone for a mildly technical learner; a full portfolio strategy
   and valid backtest are not.
4. **The AI task has an honest role.** Codex or Claude Code implements and
   explains frozen metric definitions. It does not invent a trading system.
5. **The course creates a return habit.** Learners can compare their local
   reading with Marketworks after the course without needing a long cohort.

## Persona

### Primary learner: Karan, 25

- Lives in an Indian metro or tier-2 city and has been working for 1-4 years.
- Has one or more mutual-fund SIPs and may own a few direct stocks.
- Knows the Nifty, moving averages, and a few popular market terms, but cannot
  yet distinguish index direction from the health of the wider market.
- Uses ChatGPT, Claude, or Perplexity for chats and search.
- Can install an app, download a folder, and follow a terminal walkthrough, but
  does not identify as a programmer.
- Wants an understandable process, not another stream of market opinions.

### Jobs to be done

- “Tell me what the index is hiding.”
- “Help me understand whether participation is broad or narrow.”
- “Show me how a quant turns a market idea into a measurement.”
- “Help me see which sectors and stocks are leading without giving me a tip.”
- “Give me a dashboard I own and can inspect.”

### Emotional outcome

The learner should finish calmer and more precise. They should be comfortable
saying “the evidence is mixed” and able to explain why a screen is an
observation list rather than an instruction to trade.

## Course design principles

1. **One daily question.** Every concept helps answer: “What state is the
   Indian market in as of this date?”
2. **State before stocks.** Broad market direction, breadth, and stress come
   before sector or security-level screens.
3. **Definitions before dashboards.** Every metric has a written definition,
   input, lookback, comparison, and failure mode before code is generated.
4. **Observation before prediction.** Trend, relative strength, and breakouts
   describe price behavior. They do not prove future returns.
5. **Context before pattern.** A breakout is read with breadth, regime,
   extension, and relative strength—not in isolation.
6. **Quantitative plus visual.** A chart structure must pass versioned numerical
   criteria and display the exact pivots and boundaries used by the detector.
   The visual audits the calculation; it does not override it.
7. **No pattern score.** Show a pass/fail criteria matrix and rejection reasons,
   not a composite confidence, quality, or buy score.
8. **AI as an implementation partner.** It may write and test code, but the
   learner owns metric definitions and signs off on every output.
9. **Data date always visible.** Freshness, universe coverage, missing symbols,
   and benchmark date are part of the dashboard, not footnotes.
10. **Conditions, not instructions.** The capstone never displays buy/sell,
   target, position size, or order language.

## The teaching loop

| Step | Learner action | Marketworks role | Habit created |
|---|---|---|---|
| Observe | Inspect a current reading | Live market context | Start with evidence |
| Define | State the metric in plain English | Linked Learn reference | Understand before calculating |
| Build | Reproduce the idea locally | Comparison surface | Prefer inspectable rules |
| Challenge | Find stale data, weak context, or false positives | Methodology benchmark | Distrust a clean-looking output |
| Summarize | Write a five-line dated market note | Daily return trigger | Separate observation from inference |

## Proposed shape

- **Duration:** three consecutive or near-consecutive days.
- **Total effort:** six instructional hours.
- **Modules:** six modules of approximately 60 minutes; two per day.
- **Module rhythm:** 15-minute concept, 15-minute Marketworks walkthrough,
  20-minute mission, and 10-minute check/debrief.
- **Formats:** concise video or live explanation, annotated product walkthrough,
  worksheet, concept check, and AI-assisted local build.
- **Capstone:** a local daily market-state dashboard plus a one-page audit and
  operating guide.
- **Completion evidence:** six module artifacts, including a running dashboard.

See `CURRICULUM.md` for the detailed sequence.

## Dashboard product contract

The capstone should answer five questions in under ten minutes:

1. **Is the broad market above or below trend?**
2. **How many stocks are participating?**
3. **Where is leadership concentrated?**
4. **Which stocks are outperforming the benchmark?**
5. **Which names match a transparent price landmark or chart structure?**

Required views:

- as-of date, source, universe, and coverage;
- broad index trend and drawdown;
- percentage of the universe above 50-day and 200-day moving averages;
- advance/decline or another single breadth-momentum view;
- sector relative strength and sector breadth;
- 126-day stock relative strength versus Nifty 50;
- simple landmark/condition watchlists for:
  - fresh 20-day breakouts above the 50-DMA;
  - fresh 52-week breakouts above the 50-DMA; and
  - low-volatility coiled springs above the 50-DMA and 200-DMA;
- geometric pattern-family watchlists for:
  - converging triangle breakouts;
  - rectangle/base breakouts; and
  - bull flag breakouts;
- candidate drill-down with program-generated pivots, boundaries, breakout
  level, diagnostic values, and failed criteria;
- plain-language “what this does and does not mean” notes.

The pattern list is an **observation shortlist**. It must not rank “best
stocks,” prescribe entries, calculate position sizes, or connect to a broker.
The pattern methodology is specified in `QUANT_PATTERN_SPEC.md`.

## Recommended implementation architecture

### Pilot

- Route: `/library/courses/market-state-lab`
- Six static module pages with local progress.
- Deep-links to existing `/insights/learn/<topic>` pages.
- Downloadable worksheets.
- A versioned dashboard starter folder containing:
  - synthetic or appropriately licensed delayed price data;
  - a benchmark series;
  - a universe file and data dictionary;
  - empty or partially scaffolded dashboard, metrics, and test files;
  - one-command run scripts for macOS and Windows where practical.
- No new API, database, billing rule, alerts service, or broker integration.

### After validation

- Add a documented adapter for an approved daily data source.
- Introduce cross-device progress only if learners need it.
- Consider a recurring “market state check-in” after the intensive.
- Reuse validated local-dashboard components in a future subscriber tool only
  after data rights and support costs are understood.

## What not to build

- A generic investing curriculum or product catalogue.
- A stock-picking promise, tips product, or “top stocks today” list.
- Intraday signals, candlestick libraries, options, leverage, or order entry.
- A large pattern catalog, discretionary trendline drawing, or an image model
  that cannot expose the pivots and boundaries behind a match.
- A strategy optimizer or portfolio backtest in this course.
- Broker OAuth, API keys, alerts, order files, or automatic refresh against an
  unapproved source.
- A dashboard with more than one breadth-momentum oscillator.
- Forecast probabilities or forward-return claims for a pattern.
- Raw exchange-data redistribution before licensing rights are confirmed.

## Compliance and trust boundary

The narrower course reduces some model-portfolio risk, but a named-security
screen and AI-generated commentary can still become research content depending
on substance and presentation. Before a public pilot:

1. obtain Indian securities counsel/compliance review of the metric
   definitions, named-security outputs, pattern descriptions, and disclosures;
2. classify each dashboard panel as general market commentary, educational
   calculation, or security-specific research;
3. use synthetic or appropriately licensed delayed data and document its
   redistribution rights;
4. disclose AI's role in generating code and commentary;
5. retain the methodology, source, version, and as-of date for every output;
6. remove buy/sell, target, stop, position-size, suitability, and guaranteed
   return language; and
7. label every watchlist “observation, not recommendation.”

The February 2026 SEBI Master Circular makes an RA accountable for AI-assisted
research services and related disclosure. SEBI investor education also
describes technical analysis as price/trend/volume analysis; the course should
teach its limitations and pair it with explicit risk and data-quality checks.
This study is not a legal opinion.

## Decisions to validate in the pilot

- Does “Market State Lab” communicate a useful outcome without sounding like a
  trading-call workshop?
- Can a terminal beginner start the dashboard within 20 minutes?
- Are two modules per day cognitively manageable?
- Which AI path should be primary, with the other kept as a short appendix?
- Is Streamlit acceptable, or is a generated static HTML report more robust?
- Which daily data source can be taught and redistributed lawfully?
- Do learners understand relative strength versus RSI?
- Do they treat pattern matches as observations rather than entries?
- Does the local dashboard increase or reduce Marketworks return visits?

## Definition of a successful exploration

This study is ready to advance when the founder can approve:

- one clear promise and working title;
- the three-day, six-module sequence;
- the dashboard metric and pattern contract;
- the data and compliance boundary;
- the pilot cohort and learning metrics; and
- a small implementation scope that does not require an LMS or live trading
  infrastructure.

`PILOT.md` turns those decisions into an experiment.
