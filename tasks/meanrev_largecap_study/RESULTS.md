# Oversold mean-reversion on Nifty 100 — results (2026-08-22)

Per-trade backtest, ~2010 → 2026-08-19, current constituents. Stock
above 200DMA + index-regime filter, entry next open (0.1% slippage per
side), exit on close > 5DMA or 10-day time stop. Data-artifact trades
excluded (see PLAN.md). All numbers net of slippage.

## Headline numbers

| Variant | Trades | Win rate | Avg ret | Median | Profit factor | Hold (d) | Avg alpha | p5 | Worst |
|---|---|---|---|---|---|---|---|---|---|
| RSI(2) < 10 | 7,850 | 61.0% | +0.20% | +0.64% | 1.18 | 3.2 | +0.01% | -6.1% | -54.5% |
| RSI(2) < 5 | 4,232 | 62.7% | +0.38% | +0.74% | 1.35 | 3.2 | +0.13% | -5.9% | -47.8% |
| 4 down closes | 4,066 | 61.3% | +0.18% | +0.54% | 1.16 | 3.0 | -0.03% | -5.8% | -47.8% |
| **5d drop < -5%** | **4,212** | **62.8%** | **+0.55%** | **+0.95%** | **1.47** | **3.0** | **+0.29%** | -6.3% | -41.1% |
| RSI(2)<10, no regime | 9,990 | 61.2% | +0.18% | +0.67% | 1.15 | 3.2 | +0.01% | -6.4% | -54.5% |
| RSI(2)<10, -7% stop | 8,139 | 60.2% | +0.00% | +0.62% | 1.00 | 2.8 | -0.15% | -7.1% | **-13.6%** |

## Findings

1. **The shape is as advertised: high win rate, small wins, short
   holds.** ~61-63% of trades win, typical trade lasts 3 days, 98%
   exit on the 5DMA cross (time stop rarely binds). This is the
   opposite experience profile to the VCP/breakout family (32% WR).

2. **Severity beats oscillator readings.** The best entry is the
   crudest: a 5-day drop deeper than -5% (avg +0.55%/trade, PF 1.47,
   positive per-trade alpha). RSI(2)<5 is second. The shallow signals
   (RSI(2)<10, 4-down-days) fire almost twice as often but at half the
   per-trade edge — after another 0.1%/side of slippage they are
   roughly breakeven. Depth of the selloff, not the indicator, carries
   the signal.

3. **Consistency is the strong suit.** drop5d is positive in 14 of 17
   years, including 2020 (+0.80%/trade), 2024 (+1.16%) — the years the
   breakout study bled. Worst years are mild: 2013 -0.20%, 2018
   -0.24%, 2022 -0.26%. 2020+ subset holds up: 62.7% WR, +0.68%/trade,
   +0.30% alpha — no sign the edge is a pre-2020 relic.

4. **A hard stop destroys the edge** (classic Connors result): -7%
   stop takes RSI(2)<10 from +0.20% to 0.00%/trade because it converts
   temporary drawdowns into realized losses right before the bounce.
   The cost of skipping the stop is tail risk: ~2% of trades lose
   >10%, worst real trades were -25% (RELIANCE, COVID) and -54.5%
   (ADANIENT, Hindenburg). Risk control has to come from position
   sizing, not stops. This fits the founder's probabilistic framing:
   "6 of 10 win, and the loser tail is real."

5. **The regime filter barely matters here** — the stock-level 200DMA
   gate already does the work, and selloffs deep enough to signal
   mostly happen in tapes the index filter would allow anyway. (It
   mattered enormously for breakouts.)

6. **Signals cluster.** Average ~6.5 concurrent positions, but max 50
   (COVID). A product needs a per-day cap / ranking rule (e.g. take
   the N deepest 5-day drops), which would also concentrate the edge
   per finding 2.

## Slippage sensitivity

Numbers are at 0.1% per side. Each additional 0.1% per side costs
~0.2%/trade: at 0.2%/side, drop5d nets ~+0.35%/trade and remains
viable; RSI(2)<10 and 4-down go to ~zero. Thin-edge variants are not
robust to execution quality.

## Data-quality flag (affects more than this study)

`nse500_data_merged` contains unadjusted corporate actions:
ZYDUSLIFE 2010-04-05, MOTHERSON 2013-12-20, ADANIENT 2015-06-03
demerger, and — notably — TRENT and ANANDRATHI both on **2026-05-29**
(1:2 and 1:1 bonus signatures). The 2026 pair means recent corporate
actions are slipping through the adjustment step in the live pipeline.
Only Nifty 100 symbols were scanned; the NSE 500 set likely has more.
Follow-up belongs with the pipeline, not this study.

## Addendum (2026-08-23): capped portfolio sim, last 3 years

`capped_sim.py`: drop5d variant, entries 2023-08-23 → 2026-08-19,
max 25 concurrent positions, deepest-drop-first ranking, 4% of equity
per position, same entry/exit rules. Outputs `summary_capped25_3y.json`,
`trades_capped25_3y.csv`, `equity_capped25_3y.csv`.

- 765 trades; WR 62.7%; avg +0.78%/trade; PF 1.87; avg hold 2.9 days.
- Equity: +26.3% total (8.1% CAGR), max DD -6.1%, ann vol 6.7%,
  Sharpe 1.23. Nifty 100 total return over the window: +30.4%.
- Exposure is the story: avg 3 positions (12% of capital deployed);
  in cash entirely on 40% of days; the 25-cap binds only in cluster
  selloffs (196 signals skipped, max positions hit 25 once).
- Year split: Aug-Dec 2023 ~+4.7%, 2024 +19.4%, 2025 +1.3%, 2026 YTD
  ~flat. Nearly all P&L came from 2024's dip-rich tape; the last ~18
  months were flat (fewer, shallower selloffs; per-trade avg fell to
  +0.2% in 2025 and negative YTD 2026).
- Worst trades were real single-name events (LTIM -20.0%, MARUTI
  -11.1%), confirming sizing-not-stops as the risk control.
- The cap cost little per trade (uncapped same-window avg +1.0% vs
  +0.78% capped); at 4%/position the constraint is mostly academic
  outside crash clusters.

Product read: as a standalone equity curve it undershoots buy-and-hold
on absolute return but with ~1/5 the exposure and a -6% max DD; it is
better framed as a picks feed / satellite overlay than a full-capital
strategy. The flat 2025-26 stretch is the honest caveat to show
prospective users.

## Verdict

**Viable candidate, with one condition.** The 5d-drop variant has a
real, regime-stable, execution-robust edge with the right product
shape for retail stock picks (frequent small wins, 3-day holds,
simple story: "quality large cap, sharp selloff, still in uptrend").
The condition: tail risk is managed by sizing, not stops, so the
product must be framed and sized accordingly. Next steps if pursued:
(a) portfolio-level sim with a daily position cap + deepest-drop
ranking, (b) point-in-time universe to kill the survivorship caveat,
(c) fix the corporate-action gaps first — they directly bias any
backtest on this data.
