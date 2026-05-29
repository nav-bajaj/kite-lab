# Nifty Trader — task list

Owners: 🤖 = Claude, 👤 = user reviews.
Risk: 🔴 high (can invalidate result), 🟡 medium (changes numbers), 🟢 low (cosmetic).

## Phase 1 — Data audit + breadth signal construction

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 1.1 | Inventory NSE 500 stock panel coverage + identify pre-listing handling for breadth aggregations | 🤖 | 🟡 | ☐ |
| 1.2 | Build `breadth_signals.py`: %>DMA (50/100/200), advance-decline, McClellan Osc, net new highs/lows | 🤖 | 🟡 | ☐ |
| 1.3 | Build sector breadth: % of 10+ sector indices above N-DMA, sector dispersion | 🤖 | 🟡 | ☐ |
| 1.4 | Build `macro_signals.py`: VIX level/z-score/ROC, USDINR, gold ratio | 🤖 | 🟡 | ☐ |
| 1.5 | Visual EDA — correlation of each signal with forward 5/20-day Nifty returns | 🤖 | 🟢 | ☐ |
| 1.6 | Verify no look-ahead bias (all signals strictly use t-1 or earlier data) | 🤖 | 🔴 | ☐ |

## Phase 2 — Baseline strategy

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 2.1 | Implement simplest possible breadth signal: %>200DMA crossover at chosen thresholds | 🤖 | 🟡 | ☐ |
| 2.2 | Backtest at zero cost first — establish raw signal alpha | 🤖 | 🔴 | ☐ |
| 2.3 | Establish IS / OOS split (proposed: 2010-2018 IS / 2019-2026 OOS, after questionnaire) | 🤖 | 🔴 | ☐ |
| 2.4 | If baseline doesn't generate IS alpha, document and stop (don't compound)| 🤖 | 🔴 | ☐ |

## Phase 3 — Cost model

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 3.1 | Build `cost_model.py` with explicit-cost breakdown (STT, stamp, GST, brokerage, slippage) | 🤖 | 🔴 | ☐ |
| 3.2 | Model monthly roll cost — start with constant 10 bps/roll; later import real basis data | 🤖 | 🔴 | ☐ |
| 3.3 | Apply costs to baseline; verify cost-to-turnover ratio is sensible | 🤖 | 🔴 | ☐ |
| 3.4 | Sensitivity: how does Sharpe degrade as roll cost goes from 5 → 20 → 50 bps per roll? | 🤖 | 🟡 | ☐ |

## Phase 4 — Novel signals + signal lab

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.1 | Breadth divergence: index ROC minus breadth ROC; test as standalone + as filter | 🤖 | 🟡 | ☐ |
| 4.2 | Breadth thrust: persistent >80% advancers; test as one-shot entry signal | 🤖 | 🟡 | ☐ |
| 4.3 | Cross-sectional dispersion + breadth level — 2D classifier of regime | 🤖 | 🟡 | ☐ |
| 4.4 | VIX-conditioning: signal × VIX regime interaction | 🤖 | 🟡 | ☐ |
| 4.5 | Sector breadth term structure as rotation signal | 🤖 | 🟢 | ☐ |
| 4.6 | Cross-asset confirmation: USDINR + gold + bond yield proxy | 🤖 | 🟢 | ☐ |
| 4.7 | Asymmetric thresholds (long bar higher than short bar) | 🤖 | 🟡 | ☐ |
| 4.8 | Signal-strength position sizing (continuous, not binary) | 🤖 | 🟡 | ☐ |

## Phase 5 — Candidate strategies + robustness

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 5.1 | Combine 2-3 best signals into a candidate strategy with documented rules | 🤖 | 🔴 | ☐ |
| 5.2 | Parameter sensitivity grid: ≥80% of grid must pass Sharpe / CAGR / DD thresholds | 🤖 | 🔴 | ☐ |
| 5.3 | Sub-window stability: split history into 4 windows; each must show positive alpha | 🤖 | 🔴 | ☐ |
| 5.4 | Signal ablation: remove each component; verify it actually contributes | 🤖 | 🔴 | ☐ |
| 5.5 | Correlation analysis vs OM25/TL25/L6/COMBO — must be <0.40 for diversifier claim | 🤖 | 🔴 | ☐ |
| 5.6 | Drawdown profile — visualize when strategy underperforms B&H | 🤖 | 🟡 | ☐ |

## Phase 6 — Real futures data (conditional on alpha validation)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 6.1 | Source NIFTY F1 historical data (continuous front-month) | 👤 + 🤖 | 🔴 | ☐ |
| 6.2 | Compute actual roll-cost time series from F1 vs spot basis | 🤖 | 🔴 | ☐ |
| 6.3 | Re-run candidate strategy on real futures with actual roll costs | 🤖 | 🔴 | ☐ |
| 6.4 | Compare index-proxy vs real-futures results — quantify the optimism gap | 🤖 | 🟡 | ☐ |

## Phase 7 — Report + close-out

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 7.1 | HTML report: signal panel, equity curve, drag breakdown, robustness grid, comparison vs B&H | 🤖 | 🟡 | ☐ |
| 7.2 | Honest verdict in conclusion: ship / kill / iterate | 🤖 + 👤 | 🔴 | ☐ |
| 7.3 | If ship: tasks/nifty_trader/RESULTS.md + commit + push + PR to main | 🤖 | 🟢 | ☐ |
| 7.4 | If kill: same close-out but mark as `status: archived` in _meta.yml | 🤖 | 🟢 | ☐ |
