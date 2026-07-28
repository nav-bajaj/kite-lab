# course_development — beginner course exploration

Opened 2026-07-28 on branch `course-development`.

## Executive recommendation

Build and pilot **Marketworks Foundations: From SIP to Stock Sense**, a
four-week, eight-module course for curious Indian investors aged 22-28.

This should not feel like a video library or an exam-prep course. It should feel
like a guided first month inside the market:

1. Learn one durable idea in plain English.
2. use Marketworks to see that idea in the current market;
3. record an observation or make a small decision in a simulation;
4. compare the result with a transparent rule or benchmark; and
5. finish by building a rules-based **paper** portfolio with an AI coding agent.

The course promise is competence, not returns:

> By the end, you can explain how Indian capital markets work, compare the main
> products available to you, read market conditions without relying on
> headlines, evaluate a stock idea with a repeatable checklist, and test a
> simple portfolio rule without putting real money at risk.

## Why this fits Marketworks

Marketworks already contains most of the expensive instructional substrate:

- 22 plain-English Learn explainers and a multi-category glossary;
- market regime, stress, breadth, concentration, sector, watchlist, and
  stock-level analytics;
- four production portfolios whose different rules make portfolio design
  concrete;
- a public library and an established “conditions, not instructions” compliance
  frame; and
- a product voice built for a smart non-specialist rather than a quant.

The missing layer is sequencing. Today a learner can look up an unfamiliar
term, but there is no path from “I invest through SIPs” to “I can form and test
a market view.” The course should organize existing surfaces into that path.

## Persona

### Primary learner: Karan, 25

- Lives in an Indian metro or tier-2 city and has been working for 1-4 years.
- Has a SIP in one or more equity mutual funds.
- Knows a few company and index names and may own 2-5 stocks.
- Understands that markets fluctuate but does not yet understand market
  plumbing, product differences, drawdowns, valuation, breadth, or position
  sizing.
- Uses ChatGPT, Claude, or Perplexity for chats and search.
- Can install an app, download a file, and follow a terminal walkthrough, but
  does not identify as a programmer.
- Is curious and independent, but vulnerable to information overload, social
  proof, recent-performance chasing, and “one perfect stock” thinking.

### Jobs to be done

- “Help me understand what I already own.”
- “Teach me what people mean without making me feel behind.”
- “Show me how to judge a stock idea without giving me a tip.”
- “Help me make sense of what the Indian market is doing now.”
- “Give me a system I can inspect and improve, not a black box.”

### Emotional outcome

The learner should finish calmer, more skeptical, and more capable of asking
good questions. Excitement comes from discovery and agency, not promises of
quick gains.

## Course design principles

1. **Current market as the classroom.** Every module ends on a real
   Marketworks surface. The examples change with the market; the mental models
   remain stable.
2. **Define on use.** No unexplained acronym or assumed finance vocabulary.
3. **One output per module.** Learners build a small body of work: market map,
   product map, weather report, stock dossier, portfolio policy, strategy card,
   and journal.
4. **Rules before results.** The learner specifies the process before seeing a
   backtest.
5. **Paper before capital.** The course never asks a learner to place a trade,
   connect a broker, share holdings, or expose credentials.
6. **AI as a junior analyst.** It can translate a written rule into code and
   help test it. It cannot decide the learner's risk tolerance, verify every
   fact automatically, or make an investment suitable.
7. **Show failure honestly.** Drawdowns, costs, missing data, look-ahead,
   survivorship bias, and overfitting are first-class lessons.
8. **Marketworks is evidence, not an answer key.** The course explains how the
   platform reaches a reading and invites comparison.

## The product loop

| Step | Learner action | Marketworks role | Habit created |
|---|---|---|---|
| Observe | Inspect one current reading | Live context | Open the product with a question |
| Explain | Translate it into one sentence | Linked glossary/explainer | Define before opining |
| Test | Apply a checklist or paper rule | Screener, portfolios, history | Prefer systems to tips |
| Reflect | Record what changed or surprised them | Return visit on a later date | Update beliefs, not stories |

The course should create product interaction because the live dashboard is
needed to complete the lesson, not because it is inserted as a CTA.

## Proposed shape

- **Duration:** four weeks, two modules per week.
- **Module effort:** 30-45 minutes, split into 3-5 short lessons and one mission.
- **Formats:** 5-8 minute video, concise reading, annotated product walkthrough,
  quiz, and a downloadable worksheet or lab file.
- **Cadence:** self-paced with an optional weekly 45-minute group clinic.
- **Capstone:** a locally generated, rules-based paper-portfolio report.
- **Completion evidence:** seven learner artifacts plus a short final reflection.

See `CURRICULUM.md` for the detailed sequence.

## Recommended content architecture

### Pilot

- Route: `/library/courses/from-sip-to-stock-sense`
- Build-time course manifest alongside existing library content.
- Static modules and quizzes; progress stored in `localStorage`.
- Deep-links to existing `/insights/learn/<topic>` pages.
- Downloadable worksheets and a ZIP for the AI lab.
- No new API, database table, billing rule, or broker integration.

### After validation

- Introduce `Course`, `Module`, `Lesson`, `Quiz`, and `Artifact` schemas in the
  existing finance-content-os -> dashboard publishing contract.
- Use Clerk identity for cross-device progress only after the pilot shows that
  persistence matters.
- Add cohort/community features only if they improve completion or learning.

This respects the earlier `content_bridge` decision to defer course
infrastructure until the content case is proven.

## What not to build yet

- A broad course marketplace or LMS.
- Live classes as the only delivery method.
- Certificates with no demonstrated skill.
- A fundamental-data product the current platform cannot support.
- Automatic trade execution, broker OAuth, alerts, or order files.
- Personalized allocations or risk scores.
- A “best stocks” list, price targets, buy/sell labels, or return promises.
- A parameter optimizer that rewards the highest backtest.
- Raw exchange-data distribution before licensing rights are confirmed.

## Compliance and trust boundary

Marketworks states that SEBI Research Analyst registration is applied for. The
course can safely explore general market structure, broad indices, historical
methods, risks, and simulated rules, but the boundary becomes material when it
contains security-specific analysis, weighted baskets, performance claims, or a
model portfolio.

Before any pilot is public:

1. obtain Indian securities counsel/compliance review of every strategy and AI
   lab artifact;
2. classify each lesson as general education, general market commentary,
   research content, or model-portfolio content;
3. use delayed/synthetic data and paper portfolios unless data rights and the
   regulatory basis for another use are documented;
4. disclose AI's role in generating code or research output;
5. retain the research basis and version for any factual or performance claim;
6. include risk, conflict, methodology, data-date, and educational-purpose
   disclosures where applicable; and
7. keep “conditions, not instructions” language in every Marketworks exercise.

The February 2026 SEBI Master Circular says an RA remains responsible for
security, confidentiality, data integrity, AI-generated research services, and
disclosure of AI use. It also treats a weighted basket recommended in a
research report as a model portfolio. This study is not a legal opinion; those
rules are design inputs and a reason for a formal gate.

## Strategic alternatives considered

| Concept | Strength | Weakness | Decision |
|---|---|---|---|
| Generic investing 101 | Broadest audience | Little product differentiation | Reject |
| “Learn momentum trading” | Strong Marketworks fit | Too narrow and easily read as a promise/tip course | Reject |
| Daily market-reading bootcamp | Drives frequent product use | Leaves product and portfolio foundations uncovered | Use as a future short course |
| AI stock-picker workshop | High curiosity | Highest compliance, safety, and overfitting risk | Reject |
| Foundations + AI paper lab | Broad foundation, live product loop, memorable capstone | Requires careful scaffolding and legal review | Recommend |

## Decisions to validate in the pilot

- Does “From SIP to Stock Sense” feel inviting or too informal?
- Is four weeks short enough for this persona?
- Does the AI lab increase completion, or scare non-technical learners?
- Should learners choose Codex/Claude Code, or should the pilot support one
  primary path and one appendix?
- Can Marketworks provide a legally distributable derived dataset, or should the
  pilot use synthetic data only?
- Is the right capstone a strategy report, a 30-day observation journal, or both?
- Does course access belong inside a paid subscription or as an acquisition
  product with a subscriber-only capstone?

## Definition of a successful exploration

This study is ready to advance when the founder can approve:

- one clear course promise and title;
- the eight-module sequence;
- the AI lab safety boundary;
- the pilot cohort and metrics;
- the compliance-review brief; and
- a small implementation scope that does not require an LMS.

`PILOT.md` turns those decisions into an experiment.
