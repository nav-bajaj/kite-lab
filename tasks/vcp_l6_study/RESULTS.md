# VCP + L6 study — results (2026-08-22)

Per-trade backtest of Minervini VCP breakouts on NSE 500 (current
constituents, ~2010 → 2026-08-19), Stage-2 trend template + L6
top-quartile gate, Minervini-style exits, next-open entry, 0.2%
slippage each side. See PLAN.md for design.

## Headline numbers

| Tier | Trades | Win rate | Avg ret | Avg win | Avg loss | Avg R | Median ret | Avg alpha (2020+) |
|---|---|---|---|---|---|---|---|---|
| strict (full spec) | 10 | 50% | +6.3% | +20.0% | -7.4% | 0.95 | -1.5% | +3.7% |
| standard | 255 | 33% | +2.5% | +20.0% | -6.2% | 0.31 | -4.1% | -0.3% |
| loose | 868 | 32% | +2.1% | +20.8% | -6.6% | 0.27 | -5.2% | +0.7% |
| standard, no L6 gate | 537 | 34% | +3.3% | +21.1% | -5.9% | 0.45 | +0.5% | |
| loose, no L6 gate | 1625 | 34% | +2.5% | +20.1% | -6.3% | 0.34 | +0.9% | |

Median hold ~16-23 trading days; winners hold ~2-4 months via the
50DMA trail.

## Findings

1. **The pattern has modest positive expectancy but is mostly beta.**
   ~1/3 of breakouts work; avg win ~+20% vs avg loss ~-6% gives
   +0.3R / +2-3% per trade. But Nifty 500 itself averaged +1.6% over
   the same trade windows (breakouts cluster in rising tapes), so
   per-trade alpha is ~0-1%. The edge, such as it is, is the payoff
   asymmetry from the exit discipline, not selection.

2. **The L6 top-quartile gate does not help.** Within the same signal
   stream, splitting by L6 percentile at entry: Q4 (top quartile) is
   the *worst* bucket (WR 31.8%, avg R 0.28) vs Q2-Q3 (WR ~34-36%,
   avg R ~0.38-0.39). The trend template already enforces strong
   momentum; stacking extreme 6-month momentum on top selects extended
   names more prone to failed breakouts. Gate controls agree: removing
   it raises expectancy (0.31R → 0.45R standard) while doubling sample.

3. **The full strict spec is untradeable as written.** Chaining every
   condition in the notes (first leg 15-35% AND each contraction <85%
   of prior AND final <10% AND volume dry-up <60% AND lowest-vol day in
   last third AND accumulation AND 5-bar tightness <5%) yields **10
   trades in 16 years** across 500 symbols. Its stats (50% WR, 0.95R)
   look best but n=10 is noise. The binding gates, in order of kills
   after the shared trend/volume/L6 gates: contraction count (2,141),
   first-leg depth (1,381), base length (1,187), final-leg depth (669).

4. **Strongly regime-dependent.** Positive years: 2014, 2017, 2021,
   2023 (2023: WR 45%, avg +9.2%, alpha +5.2%). Bleeds in choppy/down
   years: 2011, 2016, 2018, 2022, 2024 (2024: WR 22%, avg -1.8%).
   A market-regime filter would matter more than pattern strictness.

5. **Exit mix** (loose tier): 42% stopped out (incl. post-partial
   breakeven stops), 56% exit on the 50DMA trail, 22% of trades reach
   the +20% partial.

## Caveats

- Survivorship bias (current constituents); overstates results,
  especially pre-2024. 2020+ subset: standard WR 27.5%, avg +1.2%,
  0.15R — weaker than full-period numbers.
- Alpha only computable 2020+ (index file starts 2020).
- No capital constraints or position limits; per-trade stats only.
- Single detector implementation; fractal-pivot choices (±5 bars,
  2% base-walk tolerance) are one reasonable parameterization.
- Data quality: `nse500_data_merged` has unadjusted corporate actions
  (found later, see `tasks/meanrev_largecap_study/PLAN.md`). Exactly
  one trade here is contaminated (ANANDRATHI 2026-04-07 in
  `trades_loose_no_l6.csv`, spans an unadjusted 1:1 bonus); effect on
  aggregate stats is negligible (~0.03% of avg ret on n=1,625).

## Verdict

As a systematic overlay for the platform: **not compelling**. The
pattern's absolute expectancy is real but small, mostly market-timing
beta, and the L6 top-quartile gate — the hypothesis under test —
subtracts rather than adds. If pursued further, the interesting
directions are (a) a regime filter (index above rising 200DMA) and
(b) the standard-tier structure without the L6 gate; not more pattern
strictness.
