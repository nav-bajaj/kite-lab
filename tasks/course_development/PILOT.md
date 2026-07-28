# Pilot plan — three-day Market State Lab

## Hypotheses

1. A six-hour intensive can teach one durable market-reading process more
   effectively than a broad multi-week foundations course.
2. Learners who compare index direction with breadth and leadership will write
   more evidence-based market descriptions.
3. Basic quantitative reasoning becomes accessible when every metric is reduced
   to universe, input, lookback, comparison, output, and failure mode.
4. A constrained local dashboard build will increase agency without requiring
   prior programming.
5. Building a small version of the Insights workflow will make Marketworks
   easier to understand and create voluntary return visits.
6. Explicit “observation, not recommendation” design can prevent pattern lists
   from being interpreted as stock picks.
7. A numerical criteria matrix plus program-drawn overlay will produce better
   pattern understanding than unaided visual recognition.

## Cohort

- 20 existing or waitlisted subscribers aged roughly 22-28.
- Has at least one mutual-fund investment or equivalent basic market exposure.
- Self-described beginner or early intermediate in direct equities.
- At least half have never used a terminal coding agent.
- Mix of macOS and Windows learners.
- No requirement to disclose portfolio values, account statements, income, or
  personal holdings.

Recruit 24 if possible, assuming pre-start attrition.

## Format

- Three days with one two-hour block per day.
- Two modules per block, approximately 60 minutes each.
- Can run on consecutive days or within one week.
- One private support channel limited to setup and course questions.
- One optional 30-minute setup check before Day 3, counted as support rather
  than course instruction.
- One 20-minute exit interview per participant.
- One seven-day follow-up to measure whether the dashboard or Marketworks was
  used after completion.

## MVP scope

### Build

- One course landing page.
- Six module pages.
- 9-12 concise videos or annotated walkthroughs.
- Six concept checks with explanatory feedback.
- Four worksheets plus dashboard audit and daily routine templates.
- Versioned AI dashboard starter ZIP.
- Synthetic or appropriately licensed delayed dataset.
- Local progress tracking.
- Privacy-minimal event instrumentation.
- Pre-course, end-of-day, completion, and seven-day follow-up surveys.

### Reuse

- Existing Marketworks design system and library shell.
- Existing Learn explainers and glossary.
- Current Pulse, breadth, sector, watchlist, and stock-detail views.
- Existing production definitions for:
  - percentage above 200-DMA;
  - sector/stock relative strength;
  - 20-day breakouts; and
  - coiled springs.
- New teaching fixtures for triangle, rectangle/base, and bull flag geometry;
  these do not imply production Marketworks signals.

### Do not build

- New backend course service or LMS.
- Cross-device progress.
- Live market-data downloader before rights and reliability are approved.
- Broker or personal portfolio integration.
- Alerts, order files, or trading automation.
- Forward-return statistics or pattern win rates.
- A pattern quality/buy score or large chart-pattern library.
- Personalized recommendations.
- Portfolio backtest or strategy optimizer.
- Certificate.
- Billing changes.

## Prototype order

Do not author all six modules before testing the two highest-friction slices.

### Slice A — market-state note

Prototype Modules 1-2 with:

- one authored universe lesson and one market-state concept lesson;
- one Indian equity-universe map and decision card;
- one annotated Marketworks walkthrough;
- three Learn links;
- one misconception check; and
- the five-line market-state artifact.

Test with five learners. Observe whether they:

- distinguish exchange, index, and research universe;
- explain why the Nifty 500 is broad but not the whole listed market;
- distinguish free-float weighting from equal-stock breadth;
- check the as-of date;
- distinguish index direction from breadth;
- describe a contradiction; and
- avoid forecast language.

### Slice B — local dashboard

Prototype the starter-kit setup, frozen `METRICS.md`, market-state/breadth
panels, one pattern list, and tests. Test with:

- two terminal beginners;
- two AI-chat users; and
- one technically confident user.

Record:

- time to first successful local run;
- installation and permission friction;
- help requests;
- whether the learner can locate the metric definition;
- whether one value can be reconciled manually; and
- whether a named match is described as a pick.

### Slice C — leadership and patterns

Prototype Module 4 after Slice B runs:

- sector and stock relative strength;
- relative strength versus RSI check;
- 20-day breakout;
- 52-week breakout; and
- coiled-spring/pre-breakout distinction;
- confirmed pivots, ATR tolerance, and completed-close confirmation;
- converging triangle breakout;
- rectangle/base breakout; and
- bull flag breakout.

For each geometric family, provide one accepted overlay and one near-match
rejected by the criteria matrix. Test whether five learners can:

- point from each diagnostic value to the corresponding chart geometry;
- explain why confirmed pivots arrive with a delay;
- reject the near-match without redrawing the lines by eye;
- distinguish a match from an outcome forecast; and
- identify context and one failure mode without being prompted to trade.

### Slice D — full pilot

Author the remaining material only after Slices A-C meet their gates.

## Success metrics

### Learning

| Metric | Pilot target |
|---|---|
| Concept-score improvement | +25 percentage points pre to post |
| Market-state note | 80% separate observation from inference |
| Index versus breadth | 85% explain why they can diverge |
| Quant anatomy | 80% identify universe, lookback, benchmark, and output |
| Relative strength | 80% distinguish RS from RSI |
| Pattern literacy | 80% reconcile one detector result with its visual overlay |
| Pattern rejection | 80% reject a near-match using the failed criterion |
| Dashboard literacy | 75% manually reconcile one displayed value |
| Safety | 100% identify watchlists as observations, not recommendations |

### Completion and usability

| Metric | Pilot target |
|---|---|
| Start rate | >=85% of enrolled learners |
| Day 1 completion | >=80% |
| Full completion | >=70% |
| Dashboard setup attempted | >=85% |
| Dashboard running by end of Day 3 | >=75% |
| Median setup time | <=20 minutes |
| Median artifacts complete | >=5 of 6 |
| Critical support requests | <=2 per learner |

### Product signal

| Metric | Pilot target |
|---|---|
| “Made Marketworks easier to understand” | >=75% agree |
| Course-driven Insights discovery | >=4 distinct surfaces per learner |
| Seven-day Marketworks return | >=60% visit on at least two separate days |
| Seven-day local-dashboard reuse | >=50% run it at least twice |
| “Would miss this if removed” | >=40% very disappointed |

Learning and independent operation outrank time-on-site.

## Suggested event model

For the pilot, use privacy-minimal identifiers and never capture local
dashboard contents.

```text
course_viewed
day_started
module_started
lesson_completed
concept_check_answered
artifact_downloaded
insight_deeplink_opened
module_completed
dashboard_kit_downloaded
dashboard_setup_self_reported
dashboard_self_reported_running
course_completed
followup_submitted
```

Useful properties:

```text
course_slug
day_number
module_id
lesson_id
attempt_number
correct
insight_destination
device_os
cohort_id
```

Do not log prompts, local filenames, symbols, pattern matches, metric values,
data files, financial information, or machine identifiers.

## Research instruments

### Pre-course

- What does a 1% rise in Nifty tell you and not tell you?
- What does market breadth mean?
- What is relative strength?
- What is the difference between a screen and a forecast?
- How would you check whether a breakout calculation is valid?
- Confidence on six course outcomes, 1-5.

### End of Day 1

- Read a fresh market snapshot aloud.
- Mark each sentence observation, inference, or unsupported.
- Name one contradiction.

### End of Day 2

- Explain a supplied metric from universe to output.
- Distinguish RS from RSI.
- Reproduce one pattern definition.
- Explain why a match may fail.

### End of Day 3

- Start the dashboard without facilitator control.
- Confirm its data date and coverage.
- Reconcile one metric manually.
- Show where definitions live.
- Explain one difference from Marketworks.
- Identify one unsafe inference.

### Exit interview

- Show me how you read the market now.
- Which panel changed your interpretation?
- What did the AI get wrong or leave uncertain?
- Did any watchlist feel like a recommendation?
- What would stop you from running the dashboard again?
- Did building locally make Marketworks clearer or less necessary?
- Would you take a follow-on course on systems or portfolio construction?

## Go/no-go gates

### Proceed to full pilot when

- 4/5 Slice A learners complete the note without facilitator wording.
- 4/5 Slice B learners get the dashboard running.
- 4/5 Slice B learners reconcile one metric.
- 4/5 Slice C learners distinguish RS from RSI.
- 5/5 Slice C learners label matches observations, not stock picks.
- No learner is encouraged to connect a broker or use real money.
- Compliance and data-rights reviewers approve or supply required changes.

### Proceed to product build when

- full completion is at least 70%;
- at least six of eight learning/usability targets are met;
- setup support is manageable on both macOS and Windows;
- follow-up shows voluntary dashboard or Marketworks reuse;
- no material recommendation misunderstanding occurs; and
- at least eight participants ask for ongoing market-state practice or a
  next-level quant course.

### Stop or redesign when

- learners treat named-security screens as trade instructions;
- setup consumes more than one-third of Day 3;
- data freshness or rights cannot be explained clearly;
- AI output cannot be audited by the learner;
- the dashboard duplicates Marketworks without teaching the methodology;
- completion falls below 50%; or
- local-dashboard use replaces Marketworks without creating deeper
  understanding.

## Likely follow-on products

Only after the intensive pilot:

1. **Market State: 10 minutes a day** — recurring practice and comparison.
2. **Quant System Builder** — hypothesis, backtest, and out-of-sample testing.
3. **Portfolio Construction Lab** — diversification, sizing, and rebalancing.
4. **Stock Research Lab** — fundamentals plus market evidence.

Derivatives, options, intraday trading, live automation, and broker integration
should not be the next course for this persona.
