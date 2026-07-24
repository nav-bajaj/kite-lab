# Donchian channel exploration — RESULTS

Ran 2026-07-22 on branch `donchian_research`. Windows and acceptance bars
pre-registered in PLAN.md / TASKS.md before any run; grid fixed at
N in {10, 20, 55, 252}; no post-hoc parameter shopping.

## Verdict summary

| Hypothesis | Verdict |
|---|---|
| H2 Donchian trailing exits on L6/OM25 | **Rejected** — IS gains do not survive OOS; existing exits already do the work |
| H1 52-week-high nearness ranking (George-Hwang) | **Rejected** — differentiated but far below the return bar; blend dominated by pure L6 |
| H3 Donchian breadth indicator | **Mostly redundant** — 252d family duplicates existing breadth; 55d family is the only semi-novel slice |
| H4 momentum-filtered breakout calls | **Filter helps modestly, product fails the validity gate** — do not publish forward-return claims; viable only as an explicitly trend-following content format |

**Decision: no production change. No new portfolio. No subscriber-facing
forward-return claims from Donchian signals.** The one optional follow-up
(founder call): a descriptive "breakout breadth" tile using
`net_channel_55`, and/or an H4-style call list published as an honest
trend-following journal (43% win rate, fat right tail) rather than as
validated recommendations — see H4 below.

---

## H2 — Donchian exit overlay (rejected)

Grid: L6 x {base, +don10, +don20, +don55}, OM25-shaped x {base 20% stop,
don10/20/55 replacing the stop, don20+stop}. 36 runs.
Run dir: `runs/h2_20260722_185006/` (regenerable).

- **IS looked good, OOS said no.** On OM25, IS Calmar improved from 1.00
  (base) to 1.12 (don20-repl) and 1.07 (don55-repl). The IS pick
  (don20-repl) then lost to base in OOS-B (Calmar 1.50 vs 1.70) and OOS-C
  (1.78 vs 1.99), passing only OOS-A (1.02 vs 1.01). Fails the
  pre-registered 3-of-3 OOS consistency bar.
- **On L6 the overlay is harmful or inert.** don10/don20 cut OOS-A CAGR by
  3-5pp with deeper drawdowns (rank exits fire first and better); don55
  triggers only 19-44 times per window — a no-op.
- **Mechanism:** exit-reason attribution shows Donchian exits mostly
  *replace* rank/stop exits rather than adding protection, while raising
  annual turnover 10-60%.

## H1 — 52-week-high nearness ranking (rejected)

Variants: GH25 (close / 252d high, top-25, production-shaped execution),
GH+L6 50/50 rank blend; comparators L6, OM25. 16 runs.
Run dir: `runs/h1_20260722_185120/`.

- **Differentiation bars: passed.** Top-25 overlap vs L6 = 24.3% (< 25%),
  daily-return corr 0.70-0.81 (borderline vs the < 0.7 bar).
- **Return bar: failed by a wide margin.** GH25 OOS CAGR 11.8-17.1%,
  Sharpe 0.42-0.65 (bar: >= 30% / >= 1.5). Worst in OOS-C (11.8%).
- **Blend dominated.** GH+L6 blend is below pure L6 in every window
  (OOS-A 15.5% vs 36.1%; OOS-B 46.4% vs 65.2%; OOS-C 21.5% vs 36.8%) —
  the GH leg dilutes momentum instead of complementing it.
- **The one confirmed literature claim: crash mitigation.** GH25 drew down
  less in both crash windows (COVID: -33.1% vs L6 -38.0%; 2025 correction:
  -18.7% vs -25.4%) — directionally consistent with FAJ 2023 — but the
  return give-up is unacceptable. The useful fragment of nearness-to-high
  already lives in TL25 v3's `(close / 126d high)^2` drawdown-control term.

## H3 — Donchian breadth (mostly redundant; descriptive only)

15 daily series (pct above prior N-day high / fresh crosses / below N-day
low / net / median channel position, N in {20, 55, 252}), 2010-06..2026-05,
written to `donchian_breadth_daily.csv` (committed). Boundary gate passed:
replica of the production `net_new_highs_pct` correlates 0.998 with
`data/breadth/breadth_daily.csv`.

- `net_channel_252` vs production `net_new_highs_pct`: **rho = 0.95** —
  redundant. `med_chanpos_252` vs `pct_above_200dma`: **rho = 0.97** —
  redundant.
- The 55-day family is the only semi-novel slice: `net_channel_55` max
  rho 0.84 (vs net_new_highs_pct), `pct_fresh_high_55` max rho 0.78 (vs
  pct_at_52w_high), `med_chanpos_55` max rho 0.77. Cross-N correlations
  0.75-0.92 — the three horizons are variations on one theme.
- Character: net-channel series mean-revert fast (AR1 half-life 1-3 days;
  spiky), channel-position medians are slow regime gauges (half-life 10,
  27, 120 days for N=20/55/252). Extremes catalog is sane: bottoms =
  2020-03 COVID days, 2011-12, 2026-03; tops = 2014-05 (Modi election),
  2023-07-31.
- **No forward-return claims tested or made** (atlas discipline). If a
  consumer appears (e.g. an insights tile), `net_channel_55` is the
  candidate and must go through `pattern_validity_study.py` for any claim.

## H4 — Momentum-filtered Donchian breakout calls (founder idea)

Simulation 2010-06..2026-05: fresh cross above prior 55-day high (also
20/10 pairing), top-quartile L6-score filter vs unfiltered control, max 25
active calls prioritized by momentum rank, next-day OHLC/4 execution,
20bps each way, P&L net of slippage. Run dir: `runs/h4_20260722_185609/`.

Headline arm (filt 55/20, capped at 25):

- **1,585 closed calls (~99/year, ~2/week), median hold 64 days.**
- **Win rate 43.7%, mean P&L +6.84%, median -2.06%** — classic
  trend-following shape: most calls lose a few percent, p95 = +56.7%.
- Portfolio-equivalent (25 equal slots): **CAGR 26.9%, Sharpe 1.33,
  MaxDD -27.1%** — well below every production portfolio.
- Good years: 2014 (+22.9% mean), 2017, 2020, 2023 (+17.1%). Bad: 2018
  (-2.7%), 2015, 2011, and notably **2025 (-2.5%) and 2026 YTD (-5.6%)** —
  the product would have looked broken for the last 18 months.

**Founder question — does the top-quartile momentum filter beat running it
on all of NSE 500?** Yes, but modestly, and the cap hides it:

- Uncapped (clean comparison): filtered mean +7.94% / win rate 44.0%
  (4,714 calls) vs unfiltered +6.96% / 42.8% (9,215 calls). The filter
  adds ~1pp expectancy and ~1.2pp win rate, and halves the call volume.
- Capped: the arms converge (6.84 vs 7.18 mean) because the 25-slot list
  is full 71-79% of days and free slots are filled by momentum rank — the
  cap + priority is itself a momentum filter. The capacity constraint, not
  the quartile screen, does most of the selection: 10,380 filtered
  breakout events (26,674 unfiltered) were skipped for capacity over the
  16 years, ~6.5x the number of calls actually issued.

**Validity gate (house 6-check protocol): FAILS.**

- 20d excess vs same-date NSE-500 baseline: **+0.49pp** (< +1.0pp bar).
- 60d excess +1.27pp but halves are inconsistent (+2.45 first half,
  +0.09 second half) — the edge has decayed within the sample.
- **Direction lift is negative at every horizon (-7 to -12pp)**: a
  breakout call is *less* likely to be up than the average NSE-500 stock
  over the same dates; the mean is carried entirely by the right tail.
  Per `VALIDITY_PROTOCOL.md` this is the "not surfaced" tier.

So: no "these calls historically returned X%" copy is publishable. The
honest framing — "trend-following entries: most calls stop out small, the
tail pays" — is a different content class the platform hasn't used, would
require exceptional care in presentation, and its recent-era stats
(2024-2026) are poor. Recommendation: do not build as a recommendation
product; if the format is still attractive, revisit as an educational /
transparency journal with the full loss distribution shown.

## H4b — Exit-rule sweep (founder iteration, 2026-07-22)

Fixed entry (fresh 20-day-high breakout, top-quartile momentum, uncapped),
10 pre-registered exit rules. Run dir: `runs/h4b_20260722_190733/`.
Entry cohort is near-identical across arms, so the validity-gate verdict
(an entry property) is unchanged; this sweep is about P&L shape.

| exit | n | win% | mean | median | p95 | hold (td) | sig-CAGR | sig-Sharpe |
|---|---|---|---|---|---|---|---|---|
| don10 | 7,715 | 40.6 | +3.45 | -2.21 | +36.5 | 22 | 27.5% | 1.25 |
| don20 | 5,709 | 43.4 | +7.76 | -2.49 | +60.0 | 42 | 28.2% | 1.32 |
| don55 | 3,373 | 47.6 | **+25.75** | -1.66 | +157.6 | 109 | 27.4% | 1.31 |
| mid20 | 9,472 | 36.3 | +1.63 | -2.41 | +24.9 | 14 | 25.0% | 1.06 |
| pct10_peak | 6,509 | 41.6 | +4.79 | -3.24 | +46.1 | 28 | 24.0% | 1.17 |
| pct15_peak | 4,461 | 45.0 | +12.76 | -2.67 | +90.8 | 64 | 26.3% | 1.30 |
| atr4_peak | 7,368 | 40.9 | +4.00 | -2.37 | +40.0 | 25 | 27.2% | 1.19 |
| time40 | 7,703 | **55.1** | +4.09 | **+1.87** | +35.5 | 41 | 26.5% | 1.19 |
| momq | 3,559 | 47.0 | +19.76 | -1.13 | +113.2 | 93 | **31.0%** | **1.44** |
| don10_or_momq | 7,803 | 40.5 | +3.25 | -2.15 | +35.3 | 21 | 27.9% | 1.26 |

Findings:

1. **Slower exits monotonically improve per-call economics.** don55 earns
   7.5x don10's expectancy and even wins per-day-held (0.24%/td vs
   0.16%/td). Fast exits (don10, mid20) whipsaw breakouts to death.
2. **The best exit is our own momentum rank.** `momq` (exit when the stock
   drops below the momentum median) posts the best signal-portfolio
   aggregate (CAGR 31.0%, Sharpe 1.44) — the Donchian breakout is best
   understood as an *entry timer for the momentum sleeve*, and momentum
   itself as the exit. The Donchian low adds nothing on top
   (don10_or_momq is just don10).
3. **time40 is the only arm with a positive median call (+1.87%, 55.1% win
   rate)** and the most stable worst-year (-3.0%). If the product must
   *feel* like recommendations (most calls should win), an unconditional
   time exit produces that shape — at the cost of the fat right tail and
   a worse p5 (-20.5%, it holds losers).
4. **Aggregate capital results are exit-insensitive** (all arms CAGR
   24-31%, MaxDD -35 to -39%): exit choice reshapes the per-call
   distribution far more than total signal profitability.
5. **The "recent era is broken" read from H4 was partly an artifact.**
   Closed-call stats exclude winners still open at study end (145-159
   open calls in slow arms, mean +17-21%). Including open calls, 2025+
   means are positive for don55 (+3.8%) and momq (+4.4%). 2018 remains
   the honest bad year across all arms.
6. **Product-shape caveat:** uncapped active counts run 42-129 concurrent
   calls; a real 20-25-slot list would bind hard on the slow-exit arms.
   If any of this ships, the capped + chosen-exit configuration must be
   re-simulated (one run) before quoting numbers.

## H4c — Productization grid: cap 50, trailing stop, 1y lookback, N250 (founder iteration 2)

Fixed: 20-day breakout entry, top-quartile momentum, cap 50 (rank
priority). Grid: universe {NSE 500, N250} x lookback {126d, 252d} x exit
{momq, momq OR 20%-from-peak}. 8 arms, winner rule pre-registered
(highest 50-slot Sharpe). Run dir: `runs/h4c_20260722_193236/`.

| arm | win% | mean | median | hold | CAGR | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|---|---|---|
| **nse500 126d momq+ts20** | 49.0 | +14.7 | -0.4 | 78 | 30.5 | **1.56** | **-24.8** | **1.23** |
| nse500 252d momq+ts20 | 48.4 | +20.5 | -0.7 | 95 | 28.4 | 1.51 | -25.3 | 1.12 |
| nse500 126d momq | 53.4 | +24.4 | +1.6 | 123 | 32.6 | 1.50 | -35.1 | 0.93 |
| n250 252d momq+ts20 | 50.5 | +22.1 | +0.2 | 100 | 26.6 | 1.49 | -24.3 | 1.09 |
| n250 252d momq | 58.8 | +49.2 | +6.2 | 201 | 29.7 | 1.48 | -35.2 | 0.85 |
| nse500 252d momq | **57.8** | **+56.5** | **+6.7** | 231 | 30.5 | 1.40 | -34.8 | 0.87 |
| n250 126d momq+ts20 | 46.6 | +12.7 | -1.3 | 72 | 25.5 | 1.36 | -20.0 | 1.27 |
| n250 126d momq | 50.4 | +18.9 | +0.2 | 106 | 27.4 | 1.33 | -32.9 | 0.83 |

Findings:

1. **The 20% trailing stop earns its place at the portfolio level.** In
   every pairing it cuts MaxDD from ~-35% to ~-20/-25% for ~2pp of CAGR;
   all four ts20 arms lead on Calmar. Winner: NSE 500 / 126d /
   momq+ts20 (Sharpe 1.56, CAGR 30.5%, MaxDD -24.8%).
2. **The 1-year lookback makes the best *recommendations*, not the best
   portfolio.** 252d + momq-only: 57.8% win rate, +56.5% mean, +6.7%
   MEDIAN per call (finally positive), 231-day median hold — but deeper
   portfolio drawdowns (-34.8%). Fewer, slower, fatter calls (~43/year).
3. **Nifty 250 fits the cap better but earns less.** Days-at-cap drops
   from 75-93% (NSE 500) to 45-67%, capacity-skips fall ~4x, CAGR gives
   up 2-5pp. A liquidity/capacity trade the founder can make later.
4. **No arm collapses** (Sharpe 1.33-1.56): the entry + momentum-exit
   core is robust to these variations; configuration tunes the shape.
5. Caveat: winner-of-8 is still selection; treat between-arm deltas as
   indicative. Entry-level validity-gate failure carries over unchanged.

Mint-brand tearsheet artifact published (grid + winner deep dive).

## H4e — US comparative study (founder iteration 3, 2026-07-24)

Same rules on S&P 500 union Nasdaq 100 (514 symbols), identical window,
costs, and 50-cap. Data: yfinance rebuild of the decluttered EODHD panel
(sub lapsed 401); parity vs the 4 surviving EODHD trial files is exact
(return corr 1.00000, 0.00% median close diff). Benchmark SPY.
Run dir: `runs/h4e_20260724_142058/`.

| arm | win% | mean | median | CAGR | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|---|---|
| us 126d momq | 55.4 | +10.5 | +1.7 | **21.9** | **0.94** | -32.2 | 0.68 |
| us 126d momq+ts20 | 52.8 | +7.7 | +0.9 | 18.1 | 0.83 | **-21.0** | **0.86** |
| us 252d momq | 56.7 | +18.7 | +4.3 | 19.7 | 0.79 | -37.1 | 0.53 |
| us 252d momq+ts20 | 52.3 | +11.0 | +1.0 | 16.5 | 0.73 | -21.4 | 0.77 |

Findings:

1. **The strategy transfers.** Every US arm beats SPY (14.9% CAGR over
   the window) by 2-7pp/yr. $1 -> $23.4 in the best arm vs $9.1 for SPY.
   Consistent with the us_equities_2017 finding that momentum signals
   generalize to US large caps.
2. **India pays roughly double per unit of risk.** Best-arm Sharpe 1.56
   (India) vs 0.94 (US); CAGR 30.5% vs 21.9%. Same engine, richer fuel.
3. **The market picks a different winner.** US best arm is 126d + plain
   momq (no stop); the 20% trail cuts DD (-32 -> -21) but costs Sharpe
   (0.94 -> 0.83), the opposite of India where the stop improved
   risk-adjusted returns. US large caps whipsaw through 20% dips.
4. **US per-call stats are friendlier, tails thinner.** 55.4% win rate
   and a positive median call (+1.65%) even at 126d, but p95 +58% vs
   India's +96%.
5. **Diversification is real: monthly winner-vs-winner correlation 0.34.**
6. Capacity binds harder in the US (days-at-cap 90-96%, ~25k skipped
   breakouts) — a larger cap is worth testing if a US sleeve ever matters.

Artifact updated with a "same rules in America" section (comparison
table, indexed overlay, disclosure of the data-source swap).

## H4f — US market-fit grid on expanded universe (2026-07-24)

Universe expanded to SP500 + NDX + SP400 (914 symbols with data; SP400
list from Wikipedia current snapshot). Grid pre-registered: cap {50,100}
x stop {none, 10xATR20 trail} x exit rank {0.50, 0.35}, lookback 126d.
Overfit guard: full window AND 2023-07..2026-05 tail reported per arm.
Run dir: `runs/h4f_20260724_144608/` (+ largecap_none_xr35 single cell).

Findings:

1. **Mid caps rejected.** Same rules on the expanded universe: CAGR flat
   (21.9%), Sharpe 0.94 -> 0.83, MaxDD -32 -> -41. Call-level split:
   mid-cap calls are worse on every stat (win 51.2% vs 53.9%, median
   +0.45% vs +1.49%); under the slow exit the gap widens (mean +11.5%
   vs +17.1%). Caveat both ways: current-snapshot SP400 excludes
   winners promoted to SP500, so the test is biased against mid caps —
   but even so there is no case to expand. Keep SP500 + NDX.
2. **Exit rank 0.35 is the real US tweak.** Better in every pairing and
   in both windows. On large caps: win 55.4 -> 59.2%, median call
   +1.65 -> +3.64%, mean +10.5 -> +15.3%, Sharpe ~unchanged (0.93),
   holds lengthen to 138td, ~69 calls/yr.
3. **ATR-scaled stop rejected** (third stop variant tested): costs
   0.07-0.13 Sharpe in every pairing, both windows. The US answer is
   genuinely no stop; the momentum rank owns the exit.
4. **Cap 100 dilutes.** 2x calls, lower Sharpe/CAGR everywhere; even
   100 slots stay full ~90% of days. Keep 50.
5. Tail rankings match full-window rankings -> tweaks are time-stable.

**Recommended US config:** SP500 + NDX, 20d breakout, top-quartile 126d
momentum, cap 50, no stop, exit at momentum rank < 0.35.
Full window 22.2% CAGR / 0.93 Sharpe / -36.3% MaxDD (SPY 14.9%);
per call 59.2% win, median +3.6%, mean +15.3%, ~6.5-month median hold.
Open symmetric follow-up: exit rank < 0.35 has not been tested on India.

## H4g — Mid-caps standalone + India exit-rank test (2026-07-24)

Run dir: `runs/h4g_20260724_150137/`. Regression check passed: the
xr50 India arms reproduce h4c numbers exactly (1,377 calls, 32.64/1.496;
1,877 calls, 30.48/1.557).

A. **US mid caps as a standalone universe: rejected, third strike.**
SP400-only, cap 50, no stop: 18.3-18.4% CAGR, Sharpe 0.63-0.65,
MaxDD -42/-45%, win ~49-51%. Worse than the large-cap arm on every
metric (22.2% / 0.93 / -36.3 / 59.2%). Beats SPY on CAGR but with far
more pain. Mid-cap question closed (mixed-pool, split-stats, and
standalone reads all agree).

B. **Exit rank 0.35 on India: generalizes — prediction wrong.** It was
expected to fail as a US-only market fit. Instead: portfolio Sharpe
~unchanged without the stop (1.489 vs 1.496) and slightly BETTER with
it (1.573 vs 1.557, same -24.6% DD), clearly better tail in all pairs,
and much better call economics (no-stop mean +35.3% vs +24.4%, median
+3.45% vs +1.61%). The slow exit is an engine improvement, not market
fit. **India recommended config updates to: momq(0.35) + 20% trail —
30.0% CAGR / 1.57 Sharpe / -24.6% MaxDD.** US keeps: momq(0.35), no
stop. The two markets now differ only in the stop.

## What we learned that wasn't a no

- The engine's `donchian_low_panel` hook works as documented; prior-window
  (shift-1) bands are mandatory or the exit can never fire (Phase 1 gate3b
  proves an inclusive window produces zero breaches).
- The breadth boundary replica (0.998) validates that our raw-CSV OHLC
  loader agrees with the production close-panel pipeline — reusable for
  any future high/low research.
- GH crash mitigation is real in NSE 500, just not worth the carry. If we
  ever need a defensive tilt lever, nearness-to-high is a confirmed
  ingredient (TL25 already holds it).
- Breakout-call P&L shape (43% win, fat tail) matches the Turtle-rules
  primary source's own description — the sim is faithful to the class.

## Reproducibility

```
source .venv/bin/activate
python tasks/donchian_channel/channel_panels.py            # Phase 1 gates
python tasks/donchian_channel/h2_donchian_exit_experiment.py
python tasks/donchian_channel/h1_nearness_experiment.py
python tasks/donchian_channel/h3_breadth_profile.py
python tasks/donchian_channel/h4_breakout_calls.py
```

Outputs land in `tasks/donchian_channel/runs/<phase>_<ts>/` (gitignored,
regenerable). Inputs: `nse500_data_merged/`, `data/static/*.csv`,
`data/benchmarks/nifty100.csv`, `indices_data_historical/NIFTY_100.csv`,
`data/breadth/breadth_daily.csv`.

Caveats: current-snapshot universe (survivorship — same-date baselines
partially cancel it; disclosed per atlas precedent); no STT/taxes beyond
20bps slippage; H4 assumes fills at next-day OHLC/4 which is optimistic
for low-liquidity breakouts.

## File index

- `LITERATURE.md` — verified literature review (Turtle primary source,
  BLL 1992, STW 1999, Park-Irwin 2007, George-Hwang 2004, India evidence)
- `channel_panels.py` — OHLC panel loader + prior-window Donchian bands +
  sanity gates
- `h2_donchian_exit_experiment.py`, `h1_nearness_experiment.py`,
  `h3_breadth_profile.py`, `h4_breakout_calls.py` — phase scripts
- `donchian_breadth_daily.csv` — H3 cached panel (committed)
- `runs/` — gitignored experiment outputs
