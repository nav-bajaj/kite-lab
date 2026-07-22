# Donchian channel exploration — TASKS

Scope locked 2026-07-22. Order: Phase 1 → H2 → H1 → H3 → H4 → close-out.

## Phase 1 — Channel panels + sanity [🤖]

- [x] `channel_panels.py`: load Date×Symbol high/low/close panels from
      `nse500_data_merged/*_day.csv` (universe-filtered), rolling N-day
      Donchian bands **shifted by 1 day** (prior-window bands, else the
      engine's `close < don_low` exit and any breakout cross can never
      fire on the day the extreme is set).
- [x] Sanity gates (breadth-atlas style): spot-check RELIANCE bands vs
      manual computation; assert no `.shift(-N)` / centered rollings;
      coverage counts per year; NaN policy documented.
      Risk: silent misalignment between panel calendar and engine calendar.

## Phase 2 — H2: Donchian exit overlay [🤖]

- [x] `h2_donchian_exit_experiment.py`: L6 v2 and OM25-shaped strategies,
      exits = {baseline, don-10, don-20, don-55, don-20 + existing stop}
      across IS / OOS-A / OOS-B / OOS-C. Entries unchanged.
- [x] Pick N on IS only; verdict from OOS consistency (Calmar/MaxDD better,
      CAGR give-up <= 2pp, all three OOS windows agree in direction).
- [x] Exit-reason attribution (donchian vs rank vs stop) per window.

## Phase 3 — H1: 52-week-high nearness ranking [🤖]

- [x] `h1_nearness_experiment.py`: George-Hwang score
      `close / prior 252d high` — standalone top-25 (production-shaped
      execution) and 50/50 rank-blend with L6; comparators L6 + OM25.
- [x] Differentiation diagnostics: daily-return corr, top-25 overlap vs L6;
      "momentum in disguise" rejection per om25_alt bars.
- [x] Momentum-crash claim: drawdown comparison in 2020-03 and 2025
      correction windows.

## Phase 4 — H3: Donchian breadth indicator [🤖]

- [x] `h3_breadth_profile.py`: % of universe at prior N-day highs/lows
      (N = 20/55/252), net series, median channel position; distributions,
      dwell times, extremes catalog; correlation vs existing
      `data/breadth/breadth_daily.csv` metrics (incl. `net_new_highs_pct`
      redundancy check).
- [x] Descriptive profile only in this phase — no forward-return claims.

## Phase 5 — H4: momentum-filtered breakout calls [🤖]

- [x] `h4_breakout_calls.py`: daily simulation per PLAN spec (top-quartile
      momentum filter, 55/20 + 20/10 Turtle pairings, max 25 active,
      momentum-rank priority, next-day OHLC/4 + 20bps, P&L net of
      slippage).
- [x] Control arm: identical rules, no momentum filter (all NSE 500).
- [x] Group stats + per-year table + portfolio-equivalent equity curve.
- [x] Validity-gate dry run on the filtered calls (excess vs same-date
      NSE 500 baseline at 5/20/60d, direction lift, halves persistence).
- [ ] Overlap check vs `multi_year_breakout` fires — DEFERRED: moot while
      H4 fails the validity gate (no detector will ship); required if the
      call-list idea is ever revived.

## Phase 5b — H4 exit-rule sweep (founder request 2026-07-22) [🤖]

Fixed config: entry = fresh cross above prior 20-day high, top-quartile
momentum filter, NO slot cap, next-day OHLC/4 +/- 20bps, P&L net of
slippage. Exit grid pre-registered before any run (no post-hoc shopping):

- [x] don10 / don20 / don55 — prior N-day-low Donchian exits
- [x] mid20 — close below the 20-day channel midline
- [x] pct10_peak / pct15_peak — 10% / 15% below peak close since entry
- [x] atr4_peak — 4 x ATR20(pct) trailing from peak close
- [x] time40 — unconditional exit after 40 trading days
- [x] momq — momentum rank falls below 0.50 (loses the quartile edge)
- [x] don10_or_momq — whichever fires first
- [x] Comparison table: n, win rate, mean/median, p5/p95, hold days,
      calls/year, daily equal-weight signal-portfolio CAGR/Sharpe/MaxDD,
      per-year mean P&L stability
- [x] Note: entry cohort is (near-)identical across arms — validity-gate
      status is an ENTRY property and is not re-litigated by exit choice.

## Phase 5c — H4 productization grid (founder request 2026-07-22) [🤖]

Fixed: entry = fresh 20-day-high cross, top-quartile momentum filter,
**cap 50 active** (momentum-rank priority), next-day OHLC/4 +/- 20bps.
Grid (2 x 2 x 2 = 8 arms, pre-registered):

- [x] Universe: NSE 500 vs Nifty 250
- [x] Momentum lookback: 126d (L6-style) vs 252d (1-year), score =
      ret_N / max(annualized vol_N, 0.05), pct-rank within universe
- [x] Exit: momq (rank < 0.5) vs momq_or_ts20 (momq OR close < 0.80 x
      peak close since entry — trailing stop, first to fire)
- [x] Winner rule (pre-registered): highest 50-slot portfolio Sharpe,
      tie-break Calmar. Comparison table for all 8 arms; deep-dive
      (monthly heatmap, yearly table, open positions) on the winner.
- [x] Mint-brand HTML tearsheet (marketworks-design mint palette,
      midnight dark), published as artifact.

## Phase 6 — Close-out [👤 + 🤖]

- [x] RESULTS.md: per-hypothesis verdicts, decision line, reproducibility
      block, file index.
- [ ] Founder review: which (if any) H4 product surface to build; whether
      any H1/H2 finding warrants a production-change proposal (default
      stance: diagnostic only).
- [ ] `_meta.yml` status update.

## Risk tags

- Lookahead in hand-built panels (mitigated: shift(1) + audit gate).
- Survivorship: universe file is the current snapshot; disclose in all
  writeups (breadth-atlas precedent), baseline comparisons use same-date
  universe means to partially cancel it.
- H4 capacity rule introduces path dependence — results must be shown
  with and without the 25-slot cap to prove the cap isn't doing the work.
- Multiple-comparison discipline: parameter grid is fixed here in TASKS.md
  before any run; no post-hoc N-shopping outside {10, 20, 55, 252}.
