# portfolio_risk_2026 — plan (written retrospectively, 2026-09-04)

This folder began as a narrow question and grew into a study of drawdown and
ride quality across all four production portfolios. The plan below records how
the scope moved, because the sequence explains why later sections correct
earlier ones.

## How it started

Question: had we ever tried a rank exit buffer on L6 v2, and did it help?

Prior art said yes in-sample and no out-of-sample. `tasks/MM-tuning`
(archive branch) found buffer=6 Pareto-better on IS 2009-2016 and named
"Buffered L6 Momentum" as a candidate flagship upgrade *contingent on OOS
validation*, then locked buffer=0 and never revisited it. The only OOS
evidence came from `tasks/l6_us_tune_2026`, where an IS-selected buffer=10 lost
to buffer=0 on the S&P 500. The Indian question was genuinely open.

## How the scope grew

1. **Exit buffer on L6 v2** — answered: a turnover lever, not an alpha lever.
2. **Investor-experience lens** — the founder reframed the question from
   risk-adjusted return to what a subscriber actually lives through (rolling
   6m/12m outcomes, time underwater, Ulcer index). This became the study's
   organising frame.
3. **COMBO Defensive** — brought in as the existing "smooth ride" product,
   which produced the study's first significant correction: its true
   full-history max drawdown is -36.8%, not the -16.4% everyone had been using.
4. **Regime signals** — if COMBO's defence failed in 2018-19, why? Led to
   testing index choice (Nifty 100 / 200 / 250 / 500 / Midcap 50) and mechanic
   (moving average vs rate-of-change), then a 35-cell parameter grid.
5. **The standalone portfolios** — the same overlay tested on L6 v2 and
   OM25 v3.
6. **Production-number audit** — triggered when a study number would not
   reconcile with `docs/portfolios.md`.
7. **Walk-forward, then investor statistics and SIP** — turning a research
   result into something that could be judged as a product.

## Method held constant throughout

- One lever at a time; everything else at the production `LOCKED`/`BASELINE`
  config, including effective-dated universe membership.
- Windows matched to `oos_retune_2026` so results stay comparable to the rest
  of the research line.
- Continuous backtests sliced into windows rather than one run per window, so
  OOS periods inherit a live portfolio instead of re-warming from cash.
- Negative results recorded in full. Roughly half of this folder is things
  that did not work.

## Anti-overfit discipline

The regime work selects on an episode whose answer was already known
(2018-19), so three checks were pre-committed and all three were run:

1. A holdout period that selected nothing (2012-2015).
2. A parameter grid, to show whether the optimum is a plateau or a spike.
3. A true walk-forward, re-picking parameters annually from prior data only
   and splicing them into a single backtest.

The walk-forward is the number that should be quoted. Fixed-parameter results
appear throughout for comparison and are labelled as such.

## Scope boundary

Research only. **No production file was modified.** The output is a candidate
configuration plus an audit; both need founder decisions before anything ships.

## Critical files touched (read-only)

`scripts/_momentum_engine.py`, `scripts/_clean_engine.py`,
`scripts/om25_v3.py`, `scripts/combo_defensive.py`, `scripts/tl25_v3.py`,
`scripts/universe_membership.py`, `data/static/*_membership.csv`,
`indices_data_historical/`, `indices_data/`, `nse500_data_merged/`.
