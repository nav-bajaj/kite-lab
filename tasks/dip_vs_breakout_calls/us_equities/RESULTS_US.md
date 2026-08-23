# Dip vs breakout — US equities generalisation test (2026-08-23)

Same engine as `../experiment.py` (imported, zero code duplication), no
parameters retuned: 126d momentum score, top-quartile filter, exit at
momentum rank < 0.35, next-day OHLC/4 ± 20bps. Universe SP500 ∪
Nasdaq 100 (`data/static/us_equities_universe.csv`, 514/516 symbols
with price files), EODHD supplier-adjusted, panel 2008-01 → 2026-07-23.
Window 2010-06-01 → 2026-07-23, tail split 2023-07-01 (house
conventions). This is an out-of-sample test of the India-selected
config in the same spirit as `experiments/us_strategies_2017`.

No cliff exclusion: 88 one-day drops < -30% are real crashes (AIG
-61%, STT -59% — 2008 financials, etc.), not adjustment artifacts;
they stay in.

## Grid

| arm | calls/yr | %wks w/ call | win% | mean | median | hold (td) | CAGR | Sharpe | MaxDD | tail CAGR | tail Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bo25 | 35.1 | 46.0 | 59.0 | +16.5 | +4.0 | 138 | 24.1 | 0.95 | -38.0 | 48.0 | 1.78 |
| bo25_ts20 | 43.5 | 48.4 | 55.2 | +11.5 | +2.1 | 123 | 19.2 | 0.87 | -23.3 | 26.8 | 1.37 |
| dip25 | 45.4 | 52.6 | 55.4 | +19.2 | +3.0 | 97 | 30.9 | 1.08 | -34.4 | 56.0 | 1.80 |
| dip25_ts20 | 61.2 | 57.3 | 50.7 | +12.1 | +0.2 | 74 | 26.5 | 1.00 | -29.1 | 45.8 | 1.61 |
| **dip25_trend** | 44.9 | 51.4 | 56.0 | +19.6 | +3.1 | 98 | **31.4** | **1.10** | -34.2 | **59.0** | **1.87** |
| bo50 | 68.8 | 68.9 | 59.2 | +15.3 | +3.6 | 138 | 22.0 | 0.91 | -36.3 | 40.1 | 1.74 |
| dip50_ts20 | 114.0 | 71.2 | 51.4 | +12.0 | +0.6 | 78 | 24.7 | 0.99 | -32.2 | 40.3 | 1.56 |

## What generalises, what doesn't

- **The core finding holds: dip entry beats breakout entry into the
  same momentum sleeve.** dip25 vs bo25: CAGR 30.9% vs 24.1%, Sharpe
  1.08 vs 0.95, +10 calls/yr, 30% shorter holds. Same direction as
  India (38.4/1.63 vs 31.2/1.41), similar magnitude of gap.
- **The India headline arm does NOT transfer intact.** In India the
  20% trail helped the dip arm; on US it subtracts ~4.4pp CAGR and
  drops the median call from +3.0% to +0.2% (dip25_ts20 26.5/1.00 vs
  dip25 30.9/1.08). US momentum names appear to recover through the
  -20% level often enough that the disaster brake mostly ejects
  eventual winners. The trail's value is market-dependent, not just
  cap-dependent (the h4g finding already showed cap-dependence).
- The 200DMA gate — a no-op in India — is mildly additive on US
  (dip25_trend 31.4/1.10, best arm overall, tail 59.0% / 1.87).
- Breakout arms have no "broken tail" problem on US (bo25 tail
  48.0% / 1.78 vs India's 23.8% / 0.86) and the highest win rates
  (59%), but structurally lag on CAGR/Sharpe everywhere.
- Absolute Sharpes are ~0.5 lower than India across all arms
  (house convention: (CAGR-5%)/vol, so a US risk-free framing would
  flatter them slightly). Yearly lines are healthy: dip25 worst year
  2022 -9.9%, and 2023-2026 all strongly positive.

## Caveats

- Survivorship is *worse* here than in the India study: current
  SP500 ∪ NDX constituents are an index-winners universe over a
  16-year lookback. Headline levels are optimistic; between-arm
  deltas (shared universe) remain the reliable signal.
- 20bps slippage, no taxes; US borrow/shorting irrelevant (long-only).
- Winner-of-7 selection risk is *lower* than in the India study —
  the arms were pre-chosen there; this run changes only the panel.
- No validity-protocol run on US data; no US benchmark comparison in
  this grid (SPY 2017→2026 CAGR 15.4% per `us_strategies_2017` for
  rough context).

## Verdict

The dip-timed momentum feed is the better call product on US data
too, but the right US configuration is **dip25 or dip25_trend
(no trail)** — ~45 calls/yr, ~4.6-month median hold, 31% CAGR /
1.10 Sharpe, tail 59% / 1.87 — not the India pick dip25_ts20. If a
single cross-market config is wanted, dip25 (no trail) is the robust
middle: second-best in both markets, never the broken one.
