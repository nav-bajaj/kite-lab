# Research notes — audience, market, and product fit

Research reviewed 2026-07-28. Current numbers in this file are context for
course design, not claims to copy into marketing without rechecking their date.

## 1. What exists in the repository

### Product

Marketworks is a private-beta quantitative platform for Indian equities:

- four subscriber-visible momentum portfolios;
- a daily insight engine for market state, breadth, sectors, watchlists, and
  stock-level analytics;
- a public editorial library;
- Clerk-authenticated subscriber pages for holdings, performance, rebalances,
  and trades; and
- an explicit educational/research posture while SEBI RA registration is in
  process.

### Learning surface

The current Insights Learn hub contains:

- 22 explainers covering indicators, patterns, and concepts;
- a glossary organized across market state, breadth/momentum, patterns,
  mathematics, flows/structure, and general terms; and
- contextual links from dashboard readings to the relevant explainer.

This is a strong reference layer but not yet a curriculum. A glossary answers
“what does this mean?”; a course must answer “what should I learn next, and
what can I now do?”

### Portfolio teaching assets

The four production portfolios make abstract design choices observable:

| Portfolio | Teachable contrast |
|---|---|
| Quality Momentum | Quality of participation and regime adaptation |
| Trend Leaders | Multiple trend-quality filters |
| Core Momentum | A simpler, faster pure-momentum process |
| Defensive Blend | Combining signals and reducing exposure in bear regimes |

They can support comparison exercises without asking learners to copy holdings.
The course should discuss rule design, cadence, concentration, drawdown, and
trade-offs; it should not frame the highest historical return as the winner.

### Prior architecture decision

`tasks/content_bridge/PLAN.md` reserved
`finance-content-os/published/courses/` and `/library/courses`, but deliberately
deferred Course/Lesson schemas and paid gating. That makes a thin static pilot
the coherent next step.

## 2. Audience evidence

SEBI's Investor Survey 2025 is unusually close to the proposed persona.

### Awareness is wider than understanding

- 63% of surveyed Indian households knew at least one securities-market
  product, but only 9.5% participated.
- Awareness was 53% for mutual funds/ETFs and 49% for stocks, versus 13% for
  futures/options and roughly 10% for REITs/InvITs and corporate bonds.
- Gen Z awareness was 66% and millennial awareness 62%.
- Among investors, only 36% had moderate or high market knowledge; 64% had
  limited understanding.

This supports an “aware beginner” course rather than either absolute basics or
advanced trading.

### The demanded topics match the proposed sequence

Preferred investor-education topics included:

- frauds and scams: 59% overall;
- risk management and diversification: 44%;
- investor rights and SEBI rules: 44%;
- available investment options: 42%; and
- safe use of digital platforms: 37%.

Among people intending to invest, risk/diversification interest rose to 50% and
product-options interest to 49%. These are not optional appendices; they belong
in the core.

### Education works when people encounter it

Fewer than 1% of the nationally representative sample reported attending an
investor-education program, but 91% of attendees found the program useful.
The opportunity is discovery, accessibility, and completion—not evidence that
people reject education.

### Young participation is already structurally important

NSE reported 11.8 crore unique registered investors and 23 crore investor
accounts in July 2025, with young and first-time investors forming a meaningful
part of the new base. AMFI reported 27.86 crore mutual-fund folios and
₹82.22 lakh crore in industry AUM at 30 June 2026. Folios are not unique people,
but they show how normal the mutual-fund entry point has become.

The course bridge from mutual funds to direct-market understanding is therefore
more credible than treating every learner as a first-time saver.

## 3. The Indian-market frame to teach

“The state of the Indian market” should be a repeatable method, not a dated
lecture. Teach the learner to build a weekly market weather report from:

1. **Direction:** broad index trend and drawdown.
2. **Participation:** breadth and concentration.
3. **Leadership:** sectors and relative strength.
4. **Risk/uncertainty:** India VIX, dispersion, extension.
5. **Context:** rates, currency, commodities, events, and data date.
6. **Implication:** what the state changes about questions or risk, never a
   buy/sell instruction.

The opening lecture may provide a dated “India now” snapshot, but its numbers
must be generated near publication and carry an as-of date. Marketworks is best
used as the live layer that keeps this module fresh.

## 4. Scope decision — teach one market-reading job

The initial study proposed a broad foundations course covering market plumbing,
products, stock research, portfolio construction, and a paper-strategy
backtest. That is too much conceptual distance for a short, useful course.

The recommended intensive instead teaches one recurring job: describe the
state of the Indian equity market with dated evidence. Product education,
fundamental stock research, portfolio construction, and derivatives remain
valid follow-on topics, but they are not prerequisites for this six-hour
experience.

The narrowed scope matches the strongest existing Marketworks surfaces:

- broad index trend and drawdown;
- percentage of stocks above moving averages;
- breadth momentum and concentration;
- regime and stress context;
- sector breadth and relative strength;
- stock relative strength; and
- transparent watchlist patterns.

## 5. AI-agent opportunity — a local daily dashboard

Codex and Claude Code can help a mildly technical learner build an inspectable
local dashboard because each can:

- inspect a folder and its instructions;
- create and edit Python and presentation files;
- run tests and local commands with permission;
- explain calculations in plain language; and
- iterate on an audit and operating guide.

OpenAI's Codex guidance recommends prompts containing a goal, context,
constraints, and definition of done, plus planning and verification. Anthropic
likewise provides permission controls that can keep the learner in the approval
loop.

The agent should implement frozen metric definitions, not invent a stock screen
from the latest results. The useful conversation becomes:

- What universe and benchmark are being measured?
- What is the latest completed common data date?
- What does the metric calculate?
- Does a rolling window accidentally include today's observation?
- What happens when prices or sector mappings are missing?
- Is the output a description, screen, forecast, or recommendation?
- Can one displayed value be reproduced manually?

## 6. AI and named-security screen risks

The capstone fails educationally if it becomes “ask AI for today's best
stocks.” The design must actively surface:

- hallucinated facts and code that runs but implements the wrong definition;
- stale or incomplete data presented as current;
- current-session leakage into prior-high windows;
- survivorship bias and universe drift;
- corporate-action and missing-data errors;
- unaligned benchmark and stock dates;
- unreliable volume comparisons;
- a one-day gap dominating relative strength;
- pattern matches presented as expected returns;
- data/source licensing;
- secrets or broker credentials pasted into a prompt; and
- recommendation-like natural-language summaries.

The most important capstone output is the **dashboard audit**, not the length of
the breakout list.

## 7. Regulatory design inputs

The current February 2026 SEBI Master Circular for Research Analysts includes:

- AI-tool accountability and disclosure obligations for RAs using AI in
  research services;
- corroboration of research services with retained data and analysis; and
- model-portfolio rules for a recommended basket with security weightages.

SEBI's definition of research services also includes security
recommendations, price/stop targets, model portfolios, and trading calls.
General market trends, broad indices, and market/economic commentary are
treated differently in the research-report definition, but the precise
boundary is a legal question.

Course-design consequence: keep early exercises broad and descriptive, make
the capstone self-authored and simulated, avoid named-security prescriptions,
and obtain legal review before publication. A disclaimer does not cure a
substantive recommendation.

## 8. Content and engagement implications

The preferred instructional stack is:

- short video for first exposure;
- annotated Marketworks walkthrough for application;
- plain-language reading for durable reference;
- an immediate quiz for misconception correction;
- a small artifact for agency; and
- a return visit to see whether the market state changed.

SEBI's own 2025 website redesign brief calls for interactive courses, quizzes,
progress tracking, certificates, downloadable resources, walkthroughs, and
feedback. For Marketworks, quizzes, downloads, walkthroughs, and feedback are
worth piloting; a certificate should wait until completion reflects a real
skill.

## 9. Source log

### Indian investor and market sources

- [SEBI Investor Survey 2025 — full report and respondent data](https://www.sebi.gov.in/reports-and-statistics/research/jan-2026/investor-survey-2025-_99170.html)
- [SEBI Investor Survey 2025 — report PDF](https://www.sebi.gov.in/sebi_data/commondocs/jan-2026/Investor%20Survey%202025%20Main%20Report.pdf)
- [SEBI: how to invest in securities markets](https://investor.sebi.gov.in/securities-howtoinvest.html)
- [SEBI: investing do's and don'ts](https://investor.sebi.gov.in/securities-dos_and_donts.html)
- [SEBI February 2026 Master Circular for Research Analysts](https://www.sebi.gov.in/sebi_data/attachdocs/feb-2026/1770375507051.pdf)
- [SEBI Investor Charter](https://investor.sebi.gov.in/Investor-charter.html)
- [AMFI: Indian mutual-fund industry statistics](https://www.amfiindia.com/articles/indian-mutual)
- [NSE: July 2025 investor-account milestone](https://www.nseindia.com/mediacoverage/nse-crosses-crore-investor-accounts)
- [SEBI: Household Savings through Indian Securities Market, May 2026](https://www.sebi.gov.in/reports-and-statistics/research/may-2026/household-savings-through-indian-securities-market_101531.html)

### AI-agent sources

- [OpenAI Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [OpenAI Codex best practices](https://learn.chatgpt.com/guides/best-practices)
- [OpenAI Codex CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [Anthropic Claude Code installation](https://code.claude.com/docs/en/installation)
- [Anthropic Claude Code CLI reference](https://code.claude.com/docs/en/cli-usage)
- [Anthropic Claude Code permission modes](https://code.claude.com/docs/en/permission-modes)
- [Anthropic Claude Code security](https://code.claude.com/docs/en/security)
