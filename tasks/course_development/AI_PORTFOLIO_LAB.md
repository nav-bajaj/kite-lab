# AI Portfolio Lab — build a paper strategy on your device

## Purpose

This is the capstone for a mildly technical learner. Codex or Claude Code acts
as a local implementation partner. The learner owns the rules, reviews every
file and command, and judges the evidence.

The lab is successful if the learner can explain why the backtest may be wrong.
It is not judged on returns.

## Safety contract

The lab:

- uses a paper portfolio only;
- starts with synthetic or explicitly licensed delayed end-of-day data;
- never connects to a broker or creates an order file;
- never requests API keys, demat statements, account numbers, holdings, or
  personal financial amounts;
- never labels a named stock buy/sell/hold;
- uses a fixed, instructor-provided universe for the pilot;
- limits the learner to one signal choice and one risk rule;
- defines the test split before results are displayed; and
- records AI use in the report.

The starter folder should include a prominent `SAFETY.md`. The agent must refuse
requests to add live trading, broker authentication, leverage, options, or
automatic parameter optimization during the course.

## Starter-kit contract

Proposed download:

```text
marketworks-portfolio-lab/
  LAB_BRIEF.md
  SAFETY.md
  DATA_DICTIONARY.md
  STRATEGY_TEMPLATE.md
  PROMPTS.md
  data/
    sample_prices.csv
    sample_universe.csv
  src/
  tests/
  reports/
  requirements.txt
```

The pilot can ship empty `src/`, `tests/`, and `reports/` directories so the
learner sees the agent create the system. A later version can ship a reference
implementation in a separate, locked folder for comparison after submission.

### Dataset requirements

- Daily date, anonymized/synthetic symbol, adjusted close, and volume.
- An explicit universe-membership file by date if real historical constituents
  are used.
- Corporate-action treatment documented.
- Missing observations intentionally included for a data-quality exercise.
- A broad synthetic benchmark series.
- At least five years of daily observations so rolling behavior is visible.
- A fixed train/test boundary in `DATA_DICTIONARY.md`.

Do not redistribute NSE/vendor data until the applicable data license permits
subscriber downloads.

## Setup paths

The instructor provides graphical installation help, but the actual lab uses
only a few terminal commands.

### Codex

Current official setup supports a standalone installer on macOS/Linux:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

Then:

```bash
cd marketworks-portfolio-lab
codex
```

For an explicitly read-only first pass:

```bash
codex --sandbox read-only --ask-for-approval on-request
```

The learner can inspect `/status` and `/permissions`. After approving the plan,
restart with the normal `codex` command and keep default workspace controls.
Do not teach `--yolo` or bypass modes.

### Claude Code

Current official installation options include the native installer or package
managers. On macOS the stable Homebrew path is:

```bash
brew install --cask claude-code
```

Then begin in plan mode:

```bash
cd marketworks-portfolio-lab
claude --permission-mode plan
```

After approving the plan, restart with:

```bash
claude
```

The learner can inspect `/permissions`. Do not teach
`--dangerously-skip-permissions` or `bypassPermissions`.

Installation commands change. Recheck the linked official documentation before
recording the course walkthrough.

## Provider-neutral prompt sequence

Learners paste the same prompts into either tool. The prompts deliberately
separate design, implementation, and audit.

### Prompt 1 — understand before editing

```text
Read LAB_BRIEF.md, SAFETY.md, DATA_DICTIONARY.md, and
STRATEGY_TEMPLATE.md. Do not edit files or write code yet.

Explain the lab back to me in plain English. Then interview me one
question at a time until every blank in STRATEGY_TEMPLATE.md is explicit.
Do not suggest named securities, expected returns, or parameters based on
future test results. Flag any rule that would require data unavailable at
the decision time.

Done when: you can state my complete paper-strategy rules as an algorithm
with no subjective words such as strong, good, cheap, or soon.
```

### Prompt 2 — freeze the specification

```text
Create STRATEGY.md from our answers. It must specify:
universe, eligibility, signal, ranking or threshold, number of holdings,
weighting, entry, exit, rebalance timing, execution timing, cash treatment,
costs, benchmark, train/test dates, and failure criteria.

Add an Assumptions and Known Limitations section. Do not write backtest
code yet. Ask me to approve STRATEGY.md before continuing.
```

The instructor explicitly checks that rules were frozen before results.

### Prompt 3 — implementation plan

```text
Plan the smallest understandable Python implementation of STRATEGY.md.
Use pandas and matplotlib only unless the starter requirements already
include something else.

The plan must include tests for:
decision-time data, next-session execution, missing prices, position
weights, transaction costs, no future-data access, and the fixed
train/test split.

Keep functions small and use names a beginner can follow. Do not edit
files until I approve the plan.
```

### Prompt 4 — build and verify

```text
Implement the approved plan. Run the tests and fix failures.

Generate reports/backtest.md with:
data dates, rules, assumptions, benchmark comparison, cumulative return,
rolling 12-month return, maximum drawdown, volatility, turnover,
transaction-cost impact, train vs test results, and every limitation.

Do not call the strategy successful or recommend using it with money.
Report the exact commands you ran and the test results.
```

### Prompt 5 — red-team the result

```text
Act as a skeptical reviewer. Inspect STRATEGY.md, the code, tests, data
dictionary, and report.

Look specifically for look-ahead bias, survivorship bias, unavailable
execution prices, ignored corporate actions, missing-data handling,
benchmark mismatch, cost understatement, parameter overfitting, and claims
not supported by the output.

Write reports/audit.md. Rank findings by severity. Do not change the code.
```

### Prompt 6 — robustness without optimization

```text
Run only these pre-declared robustness checks:
1. double transaction costs;
2. shift the rebalance day by one session;
3. remove the best single calendar year;
4. summarize rolling three-year outcomes; and
5. show the worst drawdown period.

Do not search for better parameters. Append the results to
reports/robustness.md and explain what became weaker.
```

### Prompt 7 — learner explanation

```text
Create reports/strategy_card.md for a non-technical reader. Use:
idea, exact rule, why it might work, why it might fail, evidence observed,
data limitations, operational burden, and what would falsify it.

End with:
"This is a historical paper exercise, not investment advice or a forecast."
```

## Strategy rule builder

The pilot should constrain choices so the learner learns design rather than
data mining.

| Component | Pilot choice |
|---|---|
| Universe | One fixed broad teaching universe |
| Signal | Choose one: trailing return, moving-average state, or equal-weight baseline |
| Holdings | Choose from two instructor-set counts |
| Weighting | Equal weight only |
| Rebalance | Monthly only |
| Execution | Next available session after signal |
| Risk rule | Choose none or one instructor-defined broad-index rule |
| Costs | Instructor-provided baseline; robustness test at 2x |
| Benchmark | Fixed broad synthetic benchmark |
| Optimization | Prohibited |

An unconstrained lab is a later advanced course.

## Required validations

The learner checks each item in plain English:

- [ ] Every input column is defined.
- [ ] The strategy never reads a price from after its decision.
- [ ] It executes after the signal, not at the same unavailable close.
- [ ] The eligible universe reflects what was known then.
- [ ] Missing prices do not silently become zero.
- [ ] Weights sum to the intended invested percentage.
- [ ] Turnover and costs reduce returns.
- [ ] Train and test periods were fixed before results.
- [ ] Benchmark dates align.
- [ ] Drawdown is measured peak to trough.
- [ ] The report includes bad periods and limitations.
- [ ] No broker credentials or personal data exist in the folder.
- [ ] AI use and human review are disclosed.

## Instructor demo

The demo should intentionally contain a seductive bug: execute a signal at the
same day's close used to calculate it. Let the first report look unusually
good, then reveal the timeline error. This teaches skepticism more effectively
than a lecture about leakage.

## Failure memo template

The learner writes one page:

1. The result I first wanted to believe.
2. The strongest reason it may be overstated.
3. The market period where the rule struggled.
4. The assumption most likely to fail in real use.
5. The operational burden I underestimated.
6. The evidence I would need before extending the experiment.
7. Why I am keeping this as a paper strategy.

## Product connection

After the lab, compare the learner's strategy card with one Marketworks
portfolio methodology:

- Which choices are shared?
- Which risks does Marketworks handle differently?
- Which data or tests are missing from the learner version?
- How do cadence and number of holdings affect turnover and concentration?

This is a methodology comparison, not a recommendation to adopt either.

## Official setup references

- [OpenAI Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [OpenAI Codex best practices](https://learn.chatgpt.com/guides/best-practices)
- [OpenAI CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [Claude Code installation](https://code.claude.com/docs/en/installation)
- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes)
- [Claude Code security](https://code.claude.com/docs/en/security)
