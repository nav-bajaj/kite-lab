# AI Market Dashboard Lab — build a daily market desk on your device

## Purpose

This is the capstone for a mildly technical learner. Codex or Claude Code acts
as a local implementation partner. The learner owns the metric definitions,
reviews every file, and learns to challenge a dashboard rather than trust it
because it looks polished.

The lab is successful if the learner can:

- run the dashboard from a documented command;
- explain the market-state, breadth, relative-strength, and pattern panels;
- reproduce one calculation manually;
- identify stale or incomplete data; and
- explain why a named-security match is an observation, not a recommendation.

It is not evaluated on whether a pattern later “works.”

## Safety contract

The pilot:

- runs locally on the learner's device;
- uses synthetic or appropriately licensed delayed end-of-day data;
- requires no broker, demat, trading, or personal portfolio connection;
- stores no credentials, account values, holdings, or personal risk profile;
- generates no order file, alert, position size, entry price, target, or stop;
- makes no forward-return, hit-rate, or “best stock” claim;
- uses a fixed instructor-provided universe and benchmark;
- exposes the as-of date, coverage, source, and metric definitions;
- labels all named-security lists **observation, not recommendation**; and
- records AI assistance and human review in the audit.

The agent must ask before installing packages or changing permissions. The
course must not teach permissive “bypass approvals” modes.

## Starter-kit contract

```text
marketworks-market-dashboard/
├── README.md
├── AGENTS.md
├── METRICS.md
├── requirements.txt
├── app.py
├── run_dashboard.command
├── run_dashboard.bat
├── data/
│   ├── prices.csv
│   ├── benchmark.csv
│   ├── universe.csv
│   ├── sectors.csv
│   └── DATA_DICTIONARY.md
├── src/
│   ├── data.py
│   ├── market_state.py
│   ├── breadth.py
│   ├── relative_strength.py
│   ├── patterns.py
│   └── commentary.py
├── tests/
│   ├── test_data.py
│   ├── test_breadth.py
│   ├── test_relative_strength.py
│   └── test_patterns.py
└── reports/
    ├── DASHBOARD_AUDIT.md
    └── RUN_DAILY.md
```

The pilot can ship partially scaffolded files so the learner sees the agent
create the system without spending the course on setup boilerplate. A later
version may ship a reference implementation separately.

## Data contract

### `prices.csv`

Long-form daily stock data:

```text
date,symbol,close,volume
```

Requirements:

- at least 300 trading sessions for every fully covered symbol;
- `close` consistently adjusted for splits and other chosen corporate actions;
- `volume` optional, with its adjustment policy documented;
- no duplicate `(date, symbol)` rows;
- missing values remain missing rather than forward-filled silently;
- dates represent completed sessions only; and
- redistribution rights documented.

### `benchmark.csv`

```text
date,close
```

The pilot benchmark is Nifty 50 unless the instructor freezes another choice
in `METRICS.md`.

### `universe.csv`

```text
symbol,in_universe_from,in_universe_to
```

For the six-hour course, the supplied universe may be a fixed educational
snapshot. The dashboard must disclose that this creates survivorship
limitations for historical views.

### `sectors.csv`

```text
symbol,sector
```

Unknown or missing sectors must be labeled, not dropped.

## Dashboard contract

The application should be a small local Streamlit app unless the pilot finds a
generated static HTML report more reliable.

### Header

- title and educational-purpose label;
- latest completed common data date;
- benchmark and universe;
- symbol coverage and missing-data count; and
- source/methodology version.

### Panel 1 — broad market state

- benchmark close relative to its 50-DMA, 100-DMA, and 200-DMA;
- current drawdown from the trailing 252-session high;
- 20-session realized volatility; and
- plain-language descriptions with no forecast.

The local build may describe the inputs but should not recreate the production
Marketworks regime label unless its complete methodology is taught and frozen.

### Panel 2 — breadth

- percentage of covered symbols above the 50-DMA;
- percentage above the 200-DMA;
- daily advances minus declines; and
- a short history chart for the two percentage-above-DMA series.

Every breadth value shows its denominator and coverage.

### Panel 3 — sector leadership

- sector 63-day and 126-day return minus Nifty 50 return;
- percentage of covered sector constituents above the 200-DMA; and
- coverage flag for incomplete sector mappings.

### Panel 4 — stock relative strength

- 126-session stock return minus Nifty 50 return;
- top and bottom observations;
- sector and current trend context; and
- visible distinction between relative strength and RSI.

### Panel 5 — pattern observation lists

1. **Fresh 20-day breakout**
   - close today > highest close of the previous 20 sessions;
   - the prior-high window excludes today; and
   - close today > 50-DMA.

2. **Fresh 52-week breakout**
   - close today > highest close of the previous 252 sessions;
   - the prior-high window excludes today; and
   - close today > 50-DMA.

3. **Coiled spring / pre-breakout watch**
   - close today > 50-DMA and 200-DMA; and
   - recent 20-session realized volatility is below the first quartile of that
     stock's available rolling 20-session volatility history.

Each row includes:

- symbol and sector;
- as-of date;
- matched rule;
- relevant level and distance from it;
- distance from 50-DMA and 200-DMA;
- 126-session RS versus Nifty 50;
- volume ratio only if the volume series is trustworthy;
- data-quality flag; and
- a short failure-context note.

The app must never sort by an invented “buy score.”

### Panel 6 — five-line note

The agent may draft a summary only from displayed values:

1. direction;
2. participation;
3. leadership;
4. risk/volatility context; and
5. contradiction or uncertainty.

Every sentence must be traceable to one dashboard field. The learner reviews
and edits it before use.

## Setup paths

### Codex

Prerequisites:

- a supported Codex installation and account;
- Python 3.11+; and
- the extracted starter folder.

From a terminal:

```bash
cd marketworks-market-dashboard
codex
```

First prompt:

```text
Read README.md, AGENTS.md, METRICS.md, and data/DATA_DICTIONARY.md.
Do not edit anything yet. Explain the project, list the available data,
identify missing prerequisites, and propose a setup plan. Do not connect
to the internet, a broker, or any personal account.
```

The learner reviews the plan and permissions before approving installation or
file changes.

### Claude Code

Prerequisites:

- a supported Claude Code installation and account;
- Python 3.11+; and
- the extracted starter folder.

From a terminal:

```bash
cd marketworks-market-dashboard
claude
```

Use the same first prompt. The learner reviews the plan and permission settings
before any installation or edit.

## Provider-neutral prompt sequence

The instructor demonstrates one provider. The other provider uses the same
sequence with a short setup appendix.

### Prompt 1 — understand before editing

```text
Read the project instructions and data dictionary. Do not edit files.

Explain:
1. what each input file contains;
2. the latest common completed date;
3. universe and benchmark coverage;
4. which metrics are already frozen;
5. which definitions remain ambiguous;
6. the smallest environment setup; and
7. five ways this dashboard could be confidently wrong.

Ask me questions instead of filling gaps yourself.
```

### Prompt 2 — freeze `METRICS.md`

```text
Interview me one question at a time to finalize METRICS.md.

We must define:
- benchmark and universe;
- completed-session/as-of rule;
- 50, 100, and 200-DMA calculations;
- breadth denominators;
- advance/decline rule;
- 63-day and 126-day relative strength;
- 20-day and 252-day breakout rules that exclude today from the prior high;
- coiled-spring realized-volatility rule;
- missing-data and minimum-history policy;
- volume policy;
- output labels and prohibited language.

Add a What This Does Not Prove section.
Do not implement the dashboard until I approve the file.
```

### Prompt 3 — implementation plan

```text
Using only the approved METRICS.md, propose a file-by-file plan.

Separate:
1. data validation;
2. metric calculations;
3. pattern detection;
4. dashboard presentation;
5. plain-language summary; and
6. tests.

For every calculation, name at least one test. Do not edit yet.
```

### Prompt 4 — build market state and breadth

```text
Implement the approved data, market-state, and breadth plan.

Requirements:
- fail visibly on duplicate rows or unusable dates;
- never silently forward-fill stock closes;
- display latest common completed date and coverage;
- show breadth numerator and denominator;
- keep calculations outside app.py;
- add tests before rendering;
- reconcile one sample DMA and breadth value manually in the test output.

Run tests and explain failures before changing definitions.
```

### Prompt 5 — add leadership and patterns

```text
Implement sector RS, stock RS, and the three pattern lists exactly as
defined in METRICS.md.

Requirements:
- align stock and benchmark dates before calculating returns;
- distinguish relative strength from RSI in the UI;
- exclude today from prior-high breakout windows;
- require stated minimum history;
- label coiled spring as pre-breakout, not breakout;
- show context fields and data-quality flags;
- add no composite buy score, forecast, target, or recommendation;
- add focused tests for each rule.

Run the full test suite and show the result.
```

### Prompt 6 — red-team the dashboard

```text
Act as a skeptical reviewer. Do not optimize the output.

Check for:
- stale or incomplete latest dates;
- accidental future-data access;
- today included in the prior-high window;
- wrong breadth denominator;
- unaligned benchmark dates;
- insufficient moving-average history;
- survivorship and corporate-action limitations;
- misleading volume comparisons;
- missing sector coverage;
- a one-day gap dominating relative strength;
- recommendation-like language; and
- summaries that cite values not visible on screen.

Write reports/DASHBOARD_AUDIT.md with severity, evidence, and proposed
fixes. Apply only correctness and safety fixes after I approve them.
```

### Prompt 7 — create the daily operating guide

```text
Create reports/RUN_DAILY.md for a non-programmer.

Include:
- the exact start/update command;
- how to confirm the data date and coverage;
- the ten-minute reading order;
- how to write the five-line note;
- what to do when data is stale or tests fail;
- what not to infer from a pattern match;
- how to compare the reading with Marketworks; and
- how to stop the local app.

Use plain language. Do not include a trade workflow.
```

## Required validations

The learner checks every item in plain English:

- [ ] Dashboard date equals the latest completed common data date.
- [ ] Duplicate `(date, symbol)` rows stop the build.
- [ ] Missing symbols affect the displayed breadth denominator and coverage.
- [ ] A moving average appears only with the required history.
- [ ] Benchmark and stock returns use aligned dates.
- [ ] Relative strength is return minus benchmark return, not RSI.
- [ ] Breakout prior-high windows exclude the current session.
- [ ] A hand-calculated 20-day breakout example matches the code.
- [ ] A hand-calculated breadth example matches the code.
- [ ] Coiled spring is labeled pre-breakout.
- [ ] Volume context disappears or carries a warning when volume is unreliable.
- [ ] Every named-security list says observation, not recommendation.
- [ ] No buy/sell, target, stop, position size, alert, or order output exists.
- [ ] Source, as-of date, methodology version, and AI assistance are disclosed.

## Instructor demo bugs

Maintain a separate instructor-only branch or patch with:

1. a breakout window that incorrectly includes today;
2. breadth that divides by the full universe despite missing prices;
3. stock RS calculated on dates not shared with the benchmark; and
4. stale stock data combined with a current benchmark date.

Learners should detect at least two before seeing the answers.

## Dashboard audit template

The final `DASHBOARD_AUDIT.md` answers:

1. What data does the dashboard use and how fresh is it?
2. Which metrics did I reproduce manually?
3. Which outputs differ from Marketworks and why?
4. Which patterns can create false positives?
5. What would make today's summary wrong or incomplete?
6. What is intentionally absent from this dashboard?
7. Which change would require compliance or data-rights review?

## Product connection

The local build is deliberately smaller than Marketworks. The final comparison
asks:

- Which market-state readings agree?
- Are breadth differences caused by universe, date, or missing data?
- Do sector RS rankings use the same benchmark and lookback?
- Which production risk, persistence, or validation layers are absent locally?
- Which named-security observations require deeper research?

The correct conclusion is not “my dashboard replicated Marketworks.” It is:

> I understand the ingredients well enough to inspect the production reading,
> question differences, and avoid treating either screen as an instruction.

## Official setup references

- [OpenAI Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [OpenAI Codex best practices](https://learn.chatgpt.com/guides/best-practices)
- [OpenAI CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [Claude Code installation](https://code.claude.com/docs/en/installation)
- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes)
- [Claude Code security](https://code.claude.com/docs/en/security)
