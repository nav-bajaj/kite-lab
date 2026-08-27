# Hourly dip swing — results (2026-08-25)

**Verdict: no. On the only window hourly data exists for, moving the
dip feed to the hourly timeframe produces more signals and shorter
holds but destroys the edge — every swing arm is flat-to-negative
while the daily dip25_ts20 makes +7.0% on the same window and
universe. The diagnostic arms show the entry itself is the problem,
not just the tighter exits.**

## Data

- `nse500_data_hourly/`: 534 symbols, 60-min bars (7/session),
  **2025-10-15 → 2026-08-21** (~215 sessions). That is all the hourly
  history that exists anywhere in our stack — the pipeline's rolling
  90-day fetch has been accumulating since Oct 2025.
- Hourly files are raw; `apply_corporate_actions.py` heals only the
  daily dir. Healed here by aligning each day's hourly OHLC to the
  adjusted daily close (2,218 symbol-days across 71 symbols, incl.
  VEDL/TRIVENI demergers and the ANGELONE 1:10 split).
- Kite quirk found: the intraday feed switches to post-split prices
  **mid-day** on some transition days (ANGELONE 2026-02-25 switches at
  the 14:15 bar), which per-day healing can't fix. 5 symbols with
  hourly moves >25% that disagree with the daily panel by >15pp were
  excluded: ANGELONE, ECLERX, IRB, LICI, METROPOLIS. TARIL's -21% gap
  (2025-11-10) agrees with daily — real crash, kept.

## Setup

Same sleeve as dip_vs_breakout_calls: 126d vol-scaled momentum rank
from the daily panel, top quartile, 1-day lag, cap 25, rank-priority
slots, fills next bar at OHLC/4 ± 20bps. Entry timer on hourly bars
(L-bar return < -thr), swing exits (trail 8/12%, optional 70-bar time
stop), momentum-decay exit (rank < 0.35) kept as safety. Window
regime: EW universe buy-and-hold +6.3%, maxDD -16.9%.

## Grid (window return, same 10 months for all rows)

| arm | dip | exit | calls/yr | win% | median | hold (sess) | window ret | maxDD |
|---|---|---|---|---|---|---|---|---|
| h_1d3_ts8 | 1d -3% | ts8 | 372 | 31.6 | -3.7 | 10.6 | -2.1 | -17.7 |
| h_1d3_ts8_t70 | 1d -3% | ts8+70bar | 727 | 41.2 | -1.6 | 10.1 | -5.6 | -21.4 |
| h_1d3_ts12 | 1d -3% | ts12 | 157 | 27.8 | -5.4 | 24.3 | -3.7 | -19.2 |
| h_2d3_ts8 | 2d -3% | ts8 | 354 | 31.3 | -4.2 | 10.9 | -1.1 | -18.1 |
| h_2d5_ts8 | 2d -5% | ts8 | 372 | 33.2 | -3.9 | 10.6 | -3.0 | -16.6 |
| h_2d5_ts8_t70 | 2d -5% | ts8+70bar | 649 | 42.1 | -1.6 | 10.1 | -0.8 | -17.6 |
| h_2d5_ts12 | 2d -5% | ts12 | 161 | 27.0 | -6.5 | 23.9 | +0.2 | -16.0 |
| h_3d5_ts12 | 3d -5% | ts12 | 173 | 31.3 | -6.7 | 23.7 | -7.5 | -17.6 |
| h_2d5_ts20 (diag) | 2d -5% | ts20 | 68 | 20.7 | -9.9 | 50.5 | -7.2 | -18.1 |
| h_3d5_ts20 (diag) | 3d -5% | ts20 | 68 | 19.0 | -8.5 | 50.9 | +1.2 | -15.3 |
| **daily_dip25_ts20** | 5d -5% | ts20 | 55 | 21.3 | -12.1 | — | **+7.0** | **-15.0** |

(Daily benchmark re-run on the identical window and artifact-excluded
universe with the dip_vs_breakout_calls engine; its positive window
return is carried by the 25-name open book at +23.3% mean unrealized —
the slow exit lets the recovery run.)

## Why it fails

1. **The entry is the problem, not just the exits.** The diagnostic
   arms give the hourly entry the daily study's exact 20% trail and
   still lag by 6–14pp. A 1–3 session dip in a momentum name is a
   falling knife or intraday flush; the daily 5-day -5% dip selects
   *sustained* pullbacks. Shorter dip horizon = monotonically worse.
2. **Swing exits cut the payoff tail.** The daily edge's mechanism is
   holding the dip through a months-long recovery (full-study p95
   +121%). At 8–12% trails and ~10-session holds the p95 collapses to
   +12–15% while the loss side (p5 ≈ -10%) barely shrinks. Win rates
   27–42% with negative medians can't overcome that asymmetry.
3. **Costs eat what's left.** 40bps round trip on ~10-session holds:
   the best swing arms' mean call (-0.4% to -1.0%) is roughly the cost
   load — gross of costs the timeframe is breakeven at best.
4. Flow did increase as hoped — 160–730 calls/yr vs 55, fresh call in
   80–100% of weeks, slots full and thousands of signals skipped. The
   signals exist; they just aren't worth taking.

## Caveats

- **One regime slice.** 10 months, one market environment, 58–617
  closed trades/arm. The daily study rests on 16 years. If hourly ever
  matters strategically, backfill Kite 60-minute history (available
  years back, 400-day chunks) before re-testing — but the diagnostic
  arms make that low-priority: entry granularity hurt even with the
  proven exit.
- Survivorship (current constituents), winner-of-grid selection, and
  the 5-symbol artifact exclusion all flatter the hourly arms if
  anything — the true picture is likely no better.

## Addendum (2026-08-25): hourly Donchian breakout, 1m/3m momentum sleeves

Founder follow-up: same hourly panel, entry switched to a Donchian
breakout (close crosses prior N-bar high), momentum sleeve at 21td and
63td lookbacks instead of 126td. `donchian_hourly.py`; artifact
symbols excluded up front; daily 20d-breakout bo25 benchmarks (momq
exit, no stop) on the same window/universe.

| arm | channel | trail | calls/yr | win% | median | hold | window ret | Sharpe |
|---|---|---|---|---|---|---|---|---|
| h_1m_ch5s_ts8 | 5 sess | 8% | 277 | 33.6 | -3.7 | 14.0 | +7.7 | 0.28 |
| h_1m_ch10s_ts8 | 10 sess | 8% | 278 | 30.1 | -3.8 | 13.4 | +2.9 | -0.11 |
| h_1m_ch10s_ts12 | 10 sess | 12% | 199 | 31.4 | -4.5 | 21.0 | +4.2 | 0.00 |
| h_1m_ch20s_ts12 | 20 sess | 12% | 189 | 28.7 | -4.4 | 21.8 | +1.4 | -0.21 |
| h_1m_ch20s_ts20 | 20 sess | 20% | 154 | 33.6 | -3.8 | 24.0 | +1.9 | -0.16 |
| **daily_bo25_1m** | 20 d | — | **150** | **41.7** | -2.0 | — | **+23.0** | **1.20** |
| h_3m_ch5s_ts8 | 5 sess | 8% | 243 | 33.0 | -3.7 | 12.6 | +9.1 | 0.41 |
| h_3m_ch10s_ts8 | 10 sess | 8% | 242 | 31.2 | -4.0 | 13.0 | +8.0 | 0.32 |
| **h_3m_ch10s_ts12** | 10 sess | 12% | 118 | 30.0 | -6.6 | 29.4 | **+15.9** | 0.89 |
| h_3m_ch20s_ts12 | 20 sess | 12% | 127 | 26.9 | -6.8 | 24.2 | +0.1 | -0.33 |
| h_3m_ch20s_ts20 | 20 sess | 20% | 61 | 25.0 | -7.9 | 59.4 | +1.9 | -0.20 |
| daily_bo25_3m | 20 d | — | 51 | 32.6 | -5.2 | — | +19.5 | 0.96 |

Control: daily bo25 with the production 126td rank on the same
window/universe returns **+21.8%** — all three daily lookbacks cluster
(+19.5 to +23.0). The window was simply kind to breakouts; the short
lookbacks change *flow* (1m sleeve churns rank → 150 calls/yr vs ~50),
not return.

Findings:

- **Breakout entries survive hourly far better than dips did** — most
  arms positive (best +15.9%, Sharpe 0.89) vs the dip grid's 8-of-10
  negative. Consistent with the daily study's mechanism: breakouts
  confirm strength, dips at short horizon catch knives.
- **But the daily-entry premium persists across entry styles.** Every
  hourly arm underperforms its daily counterpart, by 7–21pp on the 1m
  sleeve and 4–19pp on 3m. Hourly win rates ~30% vs 41.7% daily —
  intraday breakouts are mostly noise the daily bar filters out.
- **daily_bo25_1m is the one lead worth remembering**: 150 calls/yr
  (~3/wk), win 41.7%, +23.0% window, Sharpe 1.20, maxDD -12.6% — swing
  economics from a *daily* signal by shortening the sleeve lookback,
  not the bar size. Untested beyond this 10-month slice (the 16-year
  grid only covered 126d ranks); would need the full-history study
  before it's a candidate.
- Same caveats as the dip grid: one regime slice, survivorship,
  winner-of-grid. The window favored breakouts broadly, so even the
  positive hourly numbers ride the regime.

## Addendum 2 (2026-08-25): full-history daily grid, 1m/3m/6m sleeves

The definitive version of the lookback question: both entries (20d
breakout, 5d -5% dip), sleeves at 21/63/126td, full 2010-06 →
2026-08-21 window, dip_vs_breakout_calls engine and conventions (cliff
exclusion, cap 25, breakout no-stop / dip with ts20). The 6m arms
re-ran in the same pass so all rows share one dataset — they land
within ~1-2pp of the published table (data now through 08-21, healed
panel).

`daily_lookback_grid.py`; `summary_daily_lookback.csv`.

| arm | calls/yr | win% | hold (td) | CAGR | Sharpe | MaxDD | tail CAGR | tail Sharpe |
|---|---|---|---|---|---|---|---|---|
| bo25_1m | 224 | 46.4 | 24 | 23.8 | 1.10 | **-50.2** | 34.0 | 1.51 |
| dip25_ts20_1m | 235 | 44.0 | 15 | 24.1 | 1.11 | -40.8 | 34.3 | 1.41 |
| bo25_3m | 75 | 52.6 | 73 | 31.1 | 1.48 | -36.3 | 29.2 | 1.16 |
| **dip25_ts20_3m** | **109** | 49.3 | **50** | **35.9** | **1.65** | -38.0 | 36.5 | 1.44 |
| bo25_6m | 38 | 53.1 | 141 | 29.0 | 1.35 | -39.9 | 23.8 | 0.88 |
| dip25_ts20_6m | 65 | 49.8 | 84 | 36.7 | 1.73 | -34.6 | 37.0 | 1.49 |

Findings:

- **The 1-month sleeve is regime luck, confirmed.** Over 16 years both
  1m arms collapse to ~24% CAGR / 1.10 Sharpe; bo25_1m draws down
  -50.2% with worst years -25.7% (2018) and -20.7% (2011). The +23%
  it printed on the 10-month hourly window (Addendum 1) does not
  survive history. Kill it.
- **The 3-month dip is the real find.** dip25_ts20_3m: 35.9% CAGR /
  1.65 Sharpe / -38.0% MaxDD — within ~1pp CAGR and 0.08 Sharpe of the
  headline 6m dip, but with **109 calls/yr (~2.1/wk, fresh call 79% of
  weeks) and 50td median holds** vs 65/yr and 84td. That is "more
  signals, shorter holds" achieved on daily bars via sleeve lookback —
  the thing the hourly probes failed to deliver.
- Trade-offs vs 6m dip: choppier recent years (2025 -5.6% vs +5.2%;
  worst year -16.3% vs -11.1%) and slightly deeper MaxDD. The 6m arm
  is still the steadier portfolio; 3m buys flow with tolerable decay.
- **Dip beats breakout at every lookback** (as in the original study).
  bo25_3m improves on bo25_6m (31.1/1.48 vs 29.0/1.35) but its tail is
  the weakest of the 3m/6m rows (1.16).
- dip25_ts20_1m under-deploys: mean 16.5/25 slots active, at cap only
  22% of days — the 21d rank churns exits faster than dips refill.
- Same standing caveats: survivorship, winner-of-grid, costs at 20bps
  per side (higher churn arms bear proportionally more cost risk if
  real-world slippage exceeds that).

## Addendum 3 (2026-08-25): breakout grid — channel x trail x 1m/3m

Channels 10/20/50d, exits with and without ts20, sleeves 21/63td;
same engine/window/universe as Addendum 2. `breakout_grid.py`;
`summary_breakout_grid.csv`.

| arm | calls/yr | win% | hold | CAGR | Sharpe | MaxDD | tail CAGR | tail Sharpe | tail DD |
|---|---|---|---|---|---|---|---|---|---|
| bo10_1m_xr | 226 | 46.7 | 24 | 22.8 | 1.04 | -45.5 | 31.3 | 1.37 | -24.6 |
| bo10_1m_ts20 | 230 | 46.3 | 24 | 22.7 | 1.08 | -36.3 | 28.6 | 1.24 | -25.2 |
| bo20_1m_xr | 224 | 46.4 | 24 | 23.8 | 1.10 | -50.2 | 34.0 | 1.51 | -25.6 |
| bo20_1m_ts20 | 228 | 46.5 | 24 | 23.8 | 1.14 | -41.1 | 31.7 | 1.40 | -23.5 |
| bo50_1m_xr | 219 | 45.8 | 24 | 22.3 | 1.03 | -46.5 | 30.1 | 1.28 | -21.7 |
| bo50_1m_ts20 | 221 | 46.0 | 24 | 22.7 | 1.10 | -40.2 | 34.2 | 1.51 | -20.5 |
| bo10_3m_xr | 75 | 52.6 | 72 | 31.8 | 1.51 | -35.4 | 29.9 | 1.19 | -20.9 |
| bo10_3m_ts20 | 90 | 48.4 | 63 | 27.3 | 1.37 | -29.5 | 21.6 | 0.87 | -20.4 |
| bo20_3m_xr | 75 | 52.6 | 73 | 31.1 | 1.48 | -36.3 | 29.2 | 1.16 | -21.6 |
| **bo20_3m_ts20** | 88 | 48.1 | 63 | 27.2 | 1.36 | **-26.1** | 24.7 | 1.01 | -19.6 |
| bo50_3m_xr | 74 | 51.3 | 72 | 30.3 | 1.43 | -34.1 | 27.8 | 1.11 | -20.9 |
| bo50_3m_ts20 | 85 | 48.3 | 64 | 27.8 | 1.41 | -29.2 | 26.3 | 1.10 | **-17.3** |

Findings:

- **Channel length is second-order everywhere** — 10/20/50d land
  within ~1pp CAGR of each other at both lookbacks. On the 1m sleeve
  the 21d rank churns so fast that all six arms converge to identical
  24td holds; the entry timer barely matters, the exit drives it.
- **The 1m sleeve stays dead** (~23% CAGR, Sharpe ~1.1) regardless of
  channel or trail. Confirms Addendum 2 with 6 more configurations.
- **On 3m, the trail is a CAGR-for-drawdown trade**: ts20 costs ~3-4pp
  CAGR and ~0.1 Sharpe but cuts MaxDD from -34/-36 to -26/-29.
  bo20_3m_ts20's -26.1% is the best MaxDD of any daily arm in this
  research line; bo50_3m_ts20 has the best tail DD (-17.3%). Same
  direction as the published cap-50 finding — at 3m the sleeve is
  liquid enough that the trail's disaster brake pays in DD terms even
  though it costs return.
- Dip still beats breakout on CAGR/Sharpe at every matched config;
  breakout+ts20 beats dip on MaxDD.

### Winners' board going into the drawdown review

| candidate | CAGR | Sharpe | MaxDD | calls/yr | hold | why it's on the board |
|---|---|---|---|---|---|---|
| dip25_ts20_6m (prod research headline) | 36.7 | 1.73 | -34.6 | 65 | 84td | best Sharpe + CAGR |
| dip25_ts20_3m | 35.9 | 1.65 | -38.0 | 109 | 50td | near-headline economics, 2.1 calls/wk |
| bo10_3m_xr | 31.8 | 1.51 | -35.4 | 75 | 72td | best breakout return |
| bo20_3m_ts20 | 27.2 | 1.36 | -26.1 | 88 | 63td | best MaxDD |
| bo50_3m_ts20 | 27.8 | 1.41 | -29.2 | 85 | 64td | best tail DD (-17.3) |

DD-optimization levers to explore next: trail width ladder (10/15/20%)
on the dip arms, regime filter (index above/below 200DMA gate on NEW
entries only), vol-scaled position caps, and the 3m/6m rank blend.

## Addendum 4 (2026-08-25): drawdown optimization — trail ladder + regime gate + Nifty 250

Founder-directed pass over the winners' board: trail ladder (10/15/20%)
on the dip arms, NIFTY 50 > 200DMA regime gate on new entries only,
no rank blending. `dd_optimization.py`; `summary_dd_optimization.csv`;
N250 run in `report_n250.json`. Gate is risk-on ~76% of days; the
2010-06→2010-10 stretch pre-dates the 200DMA and is left ungated.

NSE 500, key rows (full table in the CSV):

| arm | calls/yr | hold | CAGR | Sharpe | MaxDD | Calmar | tail DD |
|---|---|---|---|---|---|---|---|
| **dip_6m_ts15** | 97 | 52 | **39.4** | **1.86** | -35.2 | 1.12 | -25.3 |
| dip_6m_ts20 (old headline) | 65 | 84 | 36.7 | 1.73 | -34.6 | 1.06 | -24.4 |
| dip_6m_ts10 | 185 | 26 | 36.7 | 1.70 | -33.5 | 1.10 | -24.7 |
| **dip_6m_ts15_gate** | 78 | 53 | 31.9 | 1.73 | **-21.0** | **1.52** | **-14.6** |
| dip_6m_ts10_gate | 138 | 28 | 29.5 | 1.60 | -22.9 | 1.29 | -13.8 |
| dip_3m_ts20_gate | 88 | 49 | 28.4 | 1.46 | -25.3 | 1.12 | -16.9 |
| bo20_3m_ts20_gate | 74 | 64 | 26.1 | 1.42 | -25.2 | 1.03 | -17.7 |

Nifty 250 (235 names priced, same config):

| arm | calls/yr | CAGR | Sharpe | MaxDD | tail CAGR | tail Sharpe | tail DD |
|---|---|---|---|---|---|---|---|
| n250_dip_6m_ts15 | 82 | 33.3 | 1.68 | -35.2 | 35.3 | 1.53 | -21.4 |
| n250_dip_6m_ts15_gate | 64 | 24.8 | 1.43 | -21.2 | 30.3 | 1.51 | -13.2 |

Findings:

- **The ladder improves the headline arm itself: dip_6m_ts15 strictly
  beats the published dip25_ts20** — +2.7pp CAGR (39.4 vs 36.7), +0.13
  Sharpe (1.86), 50% more calls (97/yr), 38% shorter holds (52td), at
  equal MaxDD. 15% is simply a better trail than 20% on the 6m dip.
  On the 3m sleeve the ladder goes the other way (ts20 stays best);
  tighter trails only pay where the momentum-decay exit is slow.
- **The gate halves drawdown for ~7.5pp of CAGR.** dip_6m_ts15_gate:
  -21.0% MaxDD (vs -35.2), tail DD -14.6%, Calmar 1.52 — the best
  DD-adjusted row in the entire research line. Yearly pattern is
  classic insurance: pays out in extended bear phases (2025 flips
  -5.6% → +6.2%) and costs premium in rebounds and whipsaws (2015
  35.1 → 7.9, 2022 21.9 → 5.4, 2020 56.9 → 40.6). Mean slots active
  drops 24.7 → 20.0 — capital idles when risk-off, which IS the
  mechanism.
- **Gating the breakout winners is not worth it** — bo20_3m_ts20
  gated loses 1.1pp CAGR for 0.9pp of DD. The trail already did the
  braking; the gate double-charges. Breakouts remain dominated by
  dips on every risk-adjusted view.
- **Nifty 250 confirms the config travels.** 33.3% CAGR / 1.68 Sharpe
  ungated on the large/mid universe (vs 39.4 on NSE 500 — the small
  caps carry real alpha but the core survives), with the *strongest
  tail consistency of any arm* (tail Sharpe 1.53). Gated: -21.2%
  MaxDD, tail DD -13.2%.
- Standing caveats unchanged; the gate adds one more selection layer
  (trail picked in-sample), so the walk-forward validity study is now
  mandatory before any of this ships.

## Addendum 5 (2026-08-25): dip_6m_ts15, top-40% sleeve, uncapped

Founder question: what does the feed look like with the sleeve relaxed
to top-40% momentum (rank >= 0.60) and no concurrency cap (one
position per stock only)? Calls at
`calls_ddo_dip_6m_ts15_top40_uncapped.csv`.

- **Flow: 453 closed calls/yr** — 8.7 new/wk mean (median 5, max 117
  in a single week), a fresh call in 93% of weeks. 7,345 closed calls
  over the window; 2026 YTD: 395 (Jan 65, Feb 29, **Mar 115**, Apr 18,
  May 42, Jun 52, Jul 53, Aug 21) — dip flow clusters violently in
  corrections.
- **Per call: win 44.6%, mean +8.5%, median -1.9%**, p5 -17.0 /
  p95 +66.2, median hold 46td. Exit mix 66% trail / 34% momq. Open
  book at window end: 159 positions, mean +19.1% unrealized.
- **Concurrency is the product problem: mean 104 open positions,
  p95 155, max 182.** Uncapped, the "feed" is really a ~100-name
  portfolio; no subscriber can act on it, and week-max-117 bursts land
  exactly in drawdowns.
- Equal-weight-across-open-calls curve (different normalization from
  the cap-25 slot curve, so not directly comparable): **32.5% CAGR /
  1.64 Sharpe / -36.6% MaxDD**; tail 34.8 / 1.53 / -20.7. Relaxing
  quartile→top-40% + uncapping dilutes but does not break the edge —
  the marginal (rank 0.60-0.75) dip is still a good dip, there are
  just far more of them than anyone can trade.
- Read for the product: the raw uncapped feed is a research object,
  not a subscriber feed. If more flow is wanted, raise the cap (e.g.
  50) or keep top-40% with a cap — the cap is what converts the edge
  into an actionable call list.

### Per-trade reality + partial-follower simulation (same day)

Founder concern: with ~104 open positions, subscribers will follow
only some calls. Per-trade stats and follower sims on the uncapped
stream (`calls_uncapped_with_rank.csv`):

- Distribution: win 44.6%, median -1.9%, avg winner +30.8% vs avg
  loser -9.4% (payoff 3.26); 12.7% of trades finish > +30%, 2.6%
  > +100%. **Top 10% of trades = 111% of total P&L** — the other 90%
  net negative. Miss the top 5% → mean/trade +8.5% → +1.7%; miss the
  top 10% → -1.0%.
- Rank at signal predicts quality: mean/trade +6.3% (rank 0.60-0.70)
  → +11.2% (0.80-0.90), dipping to +9.1% at 0.90-1.00. The top-40%
  relaxation adds the weakest tranche.
- **Slot-limited follower sims** (takes calls when a slot frees, 4
  seeds): 10-slot random-picker 31.5-35.4% CAGR but MaxDD -39 to
  -43%; 10-slot rank-follower 35.8% / -30.2%. 25-slot: random
  33.0-38.4% / ~-35; rank 37.5% / -33.0. Subset-following works IF
  exits are honored — the calls are dense in quality. Rank-following
  adds ~2pp CAGR and ~10pp less DD at small caps.
- Product implications: (1) cap the published feed — the cap is the
  curation; (2) publish the momentum rank with each call so partial
  followers take the best ones; (3) the real risk is exit
  indiscipline, not partial following — median call loses, so
  subscribers judging by hit-rate quit before the tail pays. Frame
  the 15% trail as a hold instruction. Probabilistic-not-predictive
  framing per the founder's standing rule.

## Addendum 6 (2026-08-25): 8-day minimum hold

Founder ask: add a minimum hold of 8 trading days. Tested on
dip_6m_ts15 gated and ungated, two interpretations: min-hold gates all
exits, or only the momentum-decay exit (trail stays live).

| variant | CAGR | Sharpe | MaxDD | win% | median call | exits <=8td |
|---|---|---|---|---|---|---|
| ts15 baseline | 39.4 | 1.86 | -35.2 | 47.6 | -1.06 | 7.7% |
| ts15 + mh8 (all exits) | 38.6 | 1.84 | **-33.5** | 48.4 | -0.74 | 0 |
| ts15 + mh8 (momq only) | 39.4 | 1.86 | -35.2 | 47.6 | -1.06 | 7.7% |
| gate baseline | 31.9 | 1.73 | -21.0 | 47.9 | -0.96 | 4.7% |
| gate + mh8 (all exits) | 31.4 | 1.68 | -21.1 | 48.2 | -0.81 | 0 |

- **The 8-day minimum hold is essentially free**: -0.8pp CAGR ungated
  (-0.5 gated), win rate and median call slightly better, and MaxDD
  *improves* ungated (-33.5 vs -35.2) — suppressing the trail in the
  first 8 days avoids selling the V-bottom of a dip that keeps
  dipping before turning.
- The momq-only variant is a no-op: the momentum-decay exit never
  fires inside 8 days (a top-quartile name can't decay to rank < 0.35
  that fast) — all quick exits were trail exits. If a min-hold is
  adopted it must gate the trail, and the numbers say that's fine.
- Only 7.7% of baseline exits were <=8td, so this is primarily a
  subscriber-experience rule (no quick flips to erode trust in call
  stability), bought for under 1pp of CAGR.

## Addendum 7 (2026-08-25): partial profit-take (50% at +20% within 20td)

Founder ask: book half the position at +20% if reached inside 20
trading days; remainder runs the normal rules (ts15 + mh8). Freed
half modeled as cash inside the slot until the call closes (no
re-deployment).

| variant | CAGR | Sharpe | MaxDD | tail DD | win% | median | p95 |
|---|---|---|---|---|---|---|---|
| ts15+mh8 | 38.6 | 1.84 | -33.5 | -24.6 | 48.4 | -0.74 | +77 |
| ts15+mh8+PT | 36.5 | 1.82 | -33.5 | -23.5 | 48.9 | -0.51 | +70 |
| gate+mh8 | 31.4 | 1.68 | -21.1 | -14.3 | 48.2 | -0.81 | +74 |
| gate+mh8+PT | 28.4 | 1.60 | -21.1 | -13.4 | 48.6 | -0.55 | +63 |

- **Costs 2.1pp CAGR ungated / 3.0pp gated; buys almost no risk
  reduction** (MaxDD identical, tail DD ~1pp better). Sharpe holds
  ungated, drops gated.
- Why: 14% of calls trigger the scale-out, and their *remaining* leg
  goes on to win 96% of the time with +35% further mean gain — a call
  that is +20% inside 20 days is precisely a tail winner. Booking
  half of it is selling the exact trades the concentration analysis
  (Addendum 5) showed carry the whole system.
- What it does buy: banked-win optics. 1 in 7 calls hands the
  subscriber a locked +20% on half within a month — likely worth
  something for perceived reliability in a retail calls product, and
  the median call improves slightly.
- Verdict: keep it out of the model economics; if wanted for product
  psychology, publish it as optional guidance ("model holds; booking
  half at +20% costs ~2-3pp CAGR long-run") — consistent with the
  probabilistic-not-predictive framing rule.

## Addendum 8 (2026-08-26): momentum sleeve — top vs third quartile

Full write-up in `QUARTILE_STUDY.md` (portfolio grid, cohort test, and
a 22-arm exit-hysteresis grid). Headline: the dip is an entry timer for
the momentum sleeve, and the sleeve is where the return lives. Third
quartile gives up 12.1pp of CAGR under a sleeve-consistent exit, and its
entry cohort has no forward edge at all (-0.01pp @20d, t=-0.1, vs
+1.02pp / t=15.1 for the top quartile) — it would fail the validity
protocol, so nothing publishable could be built on it. The founder's
point that a 0.35 rank exit is incoherent for a Q2/Q3 entry was correct
and was tested properly: four families of hysteresis (trail-only, low
absolute floor, entry-relative, rank-ratchet, plus a promotion rule)
repair the pathology — Q3 goes from 21.9 CAGR / 0.97 Sharpe / -53% DD to
28.1 / 1.40 / -37.5% — but none close the gap to the published 36.7 /
1.73 / -34.6.

### Tested and closed: momentum-rebuild as an entry (2026-08-27)

Parked on 2026-08-26, tested the next day at the cheap first cut the note
specified (cohort forward returns, no portfolio). **It has no edge. Do
not build the portfolio arm.**

Signal: a name dips (-5% over 5 days) while in the third quartile, then
its 126d momentum rank crosses back up through a threshold within N
trading days. Buy the confirmation of the rebuild. Excess is vs the
same-day equal-weight universe; `t_clust` is the date-clustered t on
daily mean excess (signals cluster in time, so the naive t is inflated —
both are in `summary_rebuild_cohort.csv`).

| cohort | n | 20d excess | t_clust | 60d excess | t_clust | median 20d | win vs univ |
|---|---|---|---|---|---|---|---|
| q1_dip (published feed) | 28,687 | **+1.02pp** | 9.20 | **+2.43pp** | 13.52 | +0.03 | 50.1% |
| q3_dip (control) | 39,990 | -0.01pp | -2.03 | -0.25pp | -2.81 | -0.79 | 45.9% |
| cross_only_75 (no dip) | 22,509 | +0.15pp | 2.24 | +0.51pp | 4.67 | -0.72 | 45.9% |
| **rebuild_t75_n20** | 1,464 | +0.01pp | 0.33 | +0.76pp | 1.72 | -1.40 | 42.2% |
| **rebuild_t75_n40** | 3,977 | +0.09pp | 0.05 | +0.32pp | 1.10 | -1.27 | 43.1% |
| **rebuild_t65_n20** | 4,107 | -0.30pp | -2.16 | -0.71pp | -2.77 | -1.55 | 42.2% |
| **rebuild_t65_n40** | 7,808 | -0.30pp | -3.44 | -0.72pp | -3.36 | -1.51 | 41.9% |

Three things kill it:

1. **No excess at either horizon.** The 0.75-threshold variants are flat
   (+0.01pp @20d, t=0.33), the 0.65 variants are significantly
   *negative*. Median excess is negative in all four (-1.3 to -1.6pp
   @20d) and win-rate-vs-universe is 42-43% — the shape is a majority of
   quiet losers, which is exactly what the top-quartile dip is not.
2. **The dip condition actively hurts.** The `cross_only_75` control —
   the same rank crossing with no dip requirement — does better than
   every rebuild variant (+0.15pp @20d, +0.51pp @60d). So the small
   amount of signal in a rank crossing belongs to momentum acceleration
   generally, and screening for a prior dip *subtracts* from it.
3. **It would fail the validity protocol** on check one, so no
   forward-return copy could ever be published on it — the same wall the
   q3 dip cohort hit.

The exit-grid result that suggested this idea (`q3_p65g20`, 28.1 CAGR)
is therefore not evidence of a rebuild edge. It is survivorship inside
the holding period: the arm looks good because it discards losers after
the fact, not because the promotion event is predictive at the moment it
fires.

### Correlation to production, measured (2026-08-27)

The ~0.87-0.90 figure this study kept citing had been computed on
2026-08-23 but never persisted — `compare_production.py` printed the
matrix and dropped it. Re-run and now saved to
`tasks/dip_vs_breakout_calls/correlation_daily.csv` and
`correlation_monthly.csv` (2023-01-01 -> 2026-08-19, L6 v2 and OM25 v3
rebuilt from their production configs).

| | L6 v2 | OM25 v3 | Nifty 500 |
|---|---|---|---|
| Dip feed, daily returns | **0.90** | **0.87** | 0.79 |
| Dip feed, monthly returns (n=43) | **0.92** | 0.83 | 0.67 |

The original number reproduces exactly. Monthly correlation to L6 is
*higher* than daily (0.92), which is the wrong direction for a
diversification story — daily co-movement can be noise, but agreeing
month after month means the same underlying exposure. The dip feed is
not a diversifier against the production book; its case remains the
product surface (timestamped calls), as recorded in the
`swing-calls-research` note.

One drift to note: OM25 v3's 2023+ CAGR now prints 45.18 vs the 43.44 in
the committed `production_comparison.csv` from 2026-08-23 — the panels
have been healed and extended since. Metrics moved, correlations did not.

## Reusable artifacts

- `experiment.py` — hourly panel loader, **daily-close healing +
  mid-day-split artifact detector** (first infra in the repo that
  makes `nse500_data_hourly/` research-safe), hourly slot simulator.
- `donchian_hourly.py` — breakout variant over the same infra.
- `daily_lookback_grid.py` — full-history daily sleeve-lookback grid.
- `breakout_grid.py` — channel x trail x sleeve breakout grid.
- `dd_optimization.py` — parametric-trail engine + NIFTY 50 regime
  gate; the drawdown-optimization pass and the Nifty 250 run.
- `heal_log.csv`, `calls_<arm>.csv`, `summary.csv` /
  `summary_donchian.csv`, `report.json` / `report_donchian.json`.
- `quartile_compare.py` / `quartile_cohort.py` / `quartile_exits.py` —
  sleeve-band engine, cohort forward-return test, exit-hysteresis grid
  (`--promote` for the promotion arms); `summary_quartile*.csv`,
  `report_quartile*.json`, `calls_q*_*.csv`, `curve_q*_*.csv`.- `rebuild_cohort.py` — momentum-rebuild cohort test (closes the parked
  idea); `summary_rebuild_cohort.csv`, `report_rebuild_cohort.json`.
- `tasks/dip_vs_breakout_calls/compare_production.py` — now persists the
  daily + monthly correlation matrices it previously only printed.
