# Robustness — Pre-Launch Adversarial Audit

## Why this task

Production portfolios (OM25 v3, TL25 v3, L6 v2, COMBO Defensive) are about
to be launched to a wider subscriber audience. Before that happens, we
need an adversarial pass over the *entire* process — data ingestion,
universe maintenance, signal generation, backtest engine, trade execution
model, risk management, and the daily production pipeline — to find any
gaps, leaks, or methodological misstep that would cause real-money
performance to diverge from backtest claims.

This is not a "verify it works" review. It's a **"find the reasons it
might lie"** review.

## What's in this folder

- `PLAN.md` — this file
- `REPORT.md` — produced by running the `backtest-skeptic` subagent
  (created in `.claude/agents/`)

## The agent

`.claude/agents/backtest-skeptic.md` — adversarial pre-launch reviewer.
Reads the project docs, audits the engine + strategies + data pipeline
against a comprehensive checklist (12 categories, from look-ahead bias
through production gaps), and produces a structured findings report
with severity ratings (CRITICAL / HIGH / MEDIUM / LOW).

Tools: Read, Grep, Glob, Bash (read-only — no Edit / Write).

## How to invoke

Explicit invocation only:

```
Use the backtest-skeptic agent to audit our backtests and portfolios
for production-readiness. Full audit, no scope restriction.
```

Or scoped:

```
Use the backtest-skeptic agent to audit just the look-ahead bias and
data leakage categories.
```

## Audit categories (12)

1. Look-ahead bias / data leakage (highest priority)
2. Survivorship bias
3. Execution mechanics realism (slippage, fills, OHLC/4)
4. Transaction costs beyond slippage (brokerage, STT, GST, LTCG/STCG)
5. Corporate actions handling
6. Calendar / timing correctness
7. Score function correctness (edge cases, NaN, divisions)
8. Risk management correctness (stops, sizing, regime overlays)
9. Cash / sizing math
10. Methodology (IS/OOS split, parameter overfitting, multiple comparison)
11. Production / live-execution gaps (market impact, liquidity, reproducibility)
12. Data quality (missing data, outliers, stitching boundaries)

## Expected output

`REPORT.md` from the agent will list findings by severity:

- **CRITICAL**: real bug that inflates backtest vs live, or data leakage
- **HIGH**: methodological gap or unrealistic assumption adding 2pp+ to expected vs live
- **MEDIUM**: unverified assumption worth checking, missing cost adjustment <2pp
- **LOW**: edge case unlikely to fire, minor calendar quirk

Each finding cites `file_path:line_number` and explains the mechanism
by which it could cause backtest results to mislead.

The report will also include a list of things specifically verified as
CORRECT — equally important so we know what NOT to worry about.

## Decision criteria for launch

After the audit:

- **Zero CRITICAL findings** → safe to launch as-is (with caveats from
  HIGH findings documented to subscribers)
- **Any CRITICAL findings** → must be fixed before launch
- **HIGH findings** require explicit acceptance with documentation
  (e.g., a "what's not modeled" disclosure to subscribers)
- **MEDIUM findings** can be addressed post-launch if material

## Status

- 2026-05-21: branch + agent created. Audit not yet run.
- Run with: `claude` then prompt the agent (see "How to invoke" above).
