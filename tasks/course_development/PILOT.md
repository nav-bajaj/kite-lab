# Pilot plan — prove learning and product pull before building an LMS

## Hypotheses

1. A sequenced course will convert the current Learn reference layer into a
   repeat Marketworks habit.
2. The “SIP to stock sense” frame will feel relevant to a young mutual-fund
   investor without promising stock-picking success.
3. A constrained AI paper lab will increase perceived agency and completion.
4. Learners who create artifacts will retain concepts better than learners who
   only watch videos.
5. The live market-weather exercise will create more authentic return visits
   than notifications or generic CTAs.

## Cohort

- 20 existing or waitlisted subscribers aged roughly 22-28.
- Must have at least one mutual-fund investment.
- Self-described beginner or early intermediate in stocks.
- Mix of Codex/Claude familiarity, including at least half who have never used a
  terminal coding agent.
- No requirement to disclose portfolio values, account statements, or income.

Recruit 24 if possible, assuming 15-20% pre-start attrition.

## Format

- Four weeks, two modules per week.
- One optional 45-minute group clinic each week.
- Private feedback channel.
- Course content released in two-module batches.
- AI lab office hour in week four.
- One 20-minute exit interview per participant.

## MVP scope

### Build

- One course landing page.
- Eight module pages.
- 16-24 short videos or annotated walkthroughs.
- Concept checks with explanatory feedback.
- Seven downloadable worksheets.
- AI lab ZIP with synthetic data.
- Local progress tracking.
- Anonymous event instrumentation.
- Start, midpoint, completion, and confidence surveys.

### Reuse

- Existing design system and marketing/library shell.
- Existing Learn explainers and glossary.
- Current Insights pages as live missions.
- Existing portfolio methodology documentation, rewritten for beginners.

### Do not build

- New backend course service.
- Cross-device progress.
- Community feed.
- Certificate.
- Billing changes.
- Real-data downloader.
- Broker integration.
- Personalized recommendations.

## Prototype order

Do not author all eight modules before testing the teaching loop.

### Slice A — market weather

Prototype Module 3 with:

- one video;
- one annotated walkthrough;
- five Learn links;
- one quiz; and
- the five-line weather artifact.

Test with five learners. Watch them use the product without intervening.

### Slice B — AI lab

Prototype the lab setup, prompts 1-5, and a synthetic dataset. Test with:

- two terminal beginners;
- two AI-chat users;
- one technically confident user.

Record setup time, approval confusion, help requests, and whether each person
can explain the timeline of the backtest.

### Slice C — full pilot

Only author the remaining modules after both slices meet their gates.

## Success metrics

### Learning

| Metric | Pilot target |
|---|---|
| Concept-score improvement | +25 percentage points from pre to post |
| Market-weather rubric | 80% distinguish observation from inference |
| Product map | 80% correctly compare stock, MF, ETF, and bond risk |
| Backtest literacy | 75% identify look-ahead in a fresh scenario |
| Safety | 100% know not to paste credentials or treat AI output as advice |

### Engagement

| Metric | Pilot target |
|---|---|
| Start rate | >=80% of enrolled learners |
| Module 3 completion | >=70% |
| Full completion | >=50% |
| Repeat Insights visits | median >=2 separate days/week |
| Artifact completion | median >=5 of 7 |
| AI lab attempted | >=60% |

### Product signal

| Metric | Pilot target |
|---|---|
| “Made Marketworks easier to use” | >=70% agree |
| “Would miss the course if removed” | >=40% very disappointed |
| Course-driven dashboard discovery | >=3 distinct Insights surfaces/learner |
| Subscriber intent | Directional only; no hard conversion claim at n=20 |

Completion and learning outrank time-on-site. Do not optimize for clicks that
do not improve understanding.

## Suggested event model

For the pilot, use privacy-minimal identifiers and avoid portfolio data.

```text
course_viewed
module_started
lesson_completed
concept_check_answered
artifact_downloaded
insight_deeplink_opened
module_completed
ai_lab_downloaded
ai_lab_self_reported_complete
course_completed
feedback_submitted
```

Useful properties:

```text
course_slug
module_id
lesson_id
attempt_number
correct
insight_destination
device_class
cohort_id
```

Do not log prompt contents, local filenames, strategy parameters, or learner
financial information.

## Research instruments

### Pre-course

- Explain the difference between a stock and an equity mutual fund.
- What does the Nifty rising tell you—and not tell you?
- How would you decide whether a stock idea deserves research?
- What do you think a backtest proves?
- Confidence on five course outcomes, 1-5.

### Weekly pulse

- Most useful idea.
- Most confusing term.
- Where you got stuck.
- Whether Marketworks answered a real question this week.
- Time spent, self-reported.

### Exit interview

- Show me how you read the market now.
- Which module changed a belief?
- What did the AI get wrong or leave uncertain?
- What would make you return next week?
- What felt like a sales pitch?
- Would you prefer this bundled, paid separately, or used as onboarding?

## Go/no-go gates

### Proceed to full pilot when

- 4/5 Slice A learners can complete the weather report without facilitator help.
- 4/5 Slice B learners create a report.
- 4/5 Slice B learners can explain signal vs execution date.
- No learner is encouraged to connect a broker or use real money.
- Compliance counsel approves or supplies required changes.

### Proceed to product build when

- full-pilot completion is at least 50%;
- learning targets are met on at least four of five core measures;
- repeat product visits increase without push reminders;
- AI lab support burden is manageable; and
- at least 8 participants independently ask for a next-level course or ongoing
  practice.

### Stop or redesign when

- learners interpret the course as security recommendations;
- the AI lab becomes the dominant support burden;
- repeat visits are driven only by completion requirements;
- artifact quality does not improve from pre-course ability; or
- compliance changes remove the practical distinction of the concept.

## Likely follow-on products

Only after the foundations pilot:

1. **Market Weather: 10 minutes a week** — recurring practice layer.
2. **Stock Research Lab** — filings plus price/market evidence.
3. **System Builder II** — out-of-sample testing and portfolio construction.
4. **Portfolio Methodologies** — deeper study of the four Marketworks systems.

Derivatives, options, intraday trading, and live automation should not be the
next course for this persona.
