# Results — every run counted; in-sample only until §4

Harness: `tasks/om25_rebuild/lib` (same engine, store, slippage 20 bps,
price return). IS 2010-01-01 → 2015-12-31; runs end 2015-12-31 so nothing
past it is simulated. Mechanics for §1: 25 positions, exit buffer 20,
monthly entry and exit, no stop, fully invested, no filter.

## §1 — score × lookback × universe (12 trials) — IS 2010-2015

Monthly entry and exit, 25 / 20, no stop, no filter. CAGR / Sharpe / MaxDD;
trades per year, hit rate, mean holding days. NIFTY 100 did 7.8% over the window.

| Universe | Score | 6m (126) | 9m (189) | 12m (252) |
|---|---|---|---|---|
| Nifty 250 | absolute | 13.3% / 0.45 / −31% | 14.6% / 0.54 / −35% | 15.2% / 0.59 / −31% |
| Nifty 250 | vol-adjusted | 17.3% / 0.78 / −30% | 17.9% / 0.80 / −30% | **19.6% / 0.96 / −22%** |
| NSE 500 | absolute | 24.4% / 0.90 / −31% | 18.8% / 0.66 / −36% | 18.7% / 0.69 / −32% |
| NSE 500 | vol-adjusted | **24.1% / 1.05 / −28%** | 22.8% / 0.99 / −27% | 21.7% / 0.97 / −27% |

Trades per year 78-167 (longer lookback, fewer trades); hit rate 43-54%;
holds 108-230 days.

Read: **volatility adjustment wins every cell**, by 0.2-0.4 of Sharpe and
with the shallower drawdown, and it is the only version whose hit rate
clears 50%. Lookback splits by universe exactly as it did for OM25 (§3k
there): Nifty 250 wants 12 months, NSE 500 wants 6, and NSE 500's
absolute-momentum row is the noisy one (0.90 at 6m, 0.66 at 9m). Against
the OM25 capture-ratio book on the same window and mechanics (23.7% / 1.50
on Nifty 250, 23.6% / 1.44 on NSE 500) the raw momentum book is 0.4-0.5 of
Sharpe behind before any filter or device; that is the gap §2-§3 have to
close. Deflation for 12 near-identical cells is small; reported at the
close of §3.

Note: §1 ran on the founder's explicit instruction before the gates were
signed; the gate values were proposed before the run and are unchanged.

## §5a — momentum-quantile eligibility (4 trials) — IS 2010-2015, labelled post-OOS

Founder's idea 2026-09-10: rank the capture ratios only within the top
quantile of stocks by trailing return over the same lookback, instead of
the whole eligible book. `mom_quantile` switch in the score (default off;
run ids unchanged). Monthly, CR, 25 / 20, return filter on.

| Pool | Nifty 250, 12m | NSE 500, 6m |
|---|---|---|
| Whole book (return filter only) | **23.7% / 1.50 / −17.0%**, hit 65% | 27.9% / 1.53 / −21.0%, hit 56% |
| Top half by momentum | 23.9% / 1.43 / −19.3%, hit 60% | 28.4% / 1.50 / −22.8%, hit 53% |
| Top quartile by momentum | 17.2% / 0.77 / −25.9%, hit 47% | 27.6% / 1.28 / −28.0%, hit 49% |

The top half is neutral; the top quartile hurts, badly on Nifty 250
(−0.73 of Sharpe, hit rate from 65% to 47%). The capture ratio already
prefers stocks that went up; forcing the pool to the fastest quartile
swaps its steady-participation names for high-beta ones with more
turnover and worse exits. Not adopted. Registered under phase 5a.

## §2 — mechanics (72 trials) — IS 2010-2015, vol-adjusted momentum

top-N ∈ {15, 20, 25} (founder cap 25) × exit buffer ∈ {0, 10, 20} ×
cadence ∈ {weekly, biweekly entry+exit, biweekly entry / weekly exit,
monthly}, on Nifty 250 12m and NSE 500 6m.

| | Nifty 250 | NSE 500 |
|---|---|---|
| §1 base, 25 / 20 / monthly | 19.6% / 0.96 / −22% (78 trades/yr) | 24.1% / 1.05 / −28% (167) |
| Best cell | 25 / 10 / weekly: 20.1% / 0.97 / −25% (149) | 20 / 20 / monthly: 25.4% / 1.10 / −28% (133) |
| Mean Sharpe by cadence | monthly 0.82 > biweekly/weekly 0.74 > biweekly 0.70 > weekly 0.69 | monthly 0.92 > 0.85 > 0.84 > weekly 0.80 |
| Mean Sharpe by top-N | 15: 0.68, 20: 0.70, **25: 0.82** | 15: 0.80, 20: 0.85, **25: 0.91** |
| Mean Sharpe by buffer | 0: 0.60, **10: 0.81**, 20: 0.80 | 0: 0.73, 10: 0.86, **20: 0.97** |

Same shape as OM25 §3i: monthly is best and cheapest, more names are
better up to the cap, and a zero buffer is the one clearly bad setting
(−0.2 of Sharpe, it churns the boundary). Weekly exits on a slower entry
add trades without Sharpe. The best cells beat the base by 0.01-0.05, well
inside noise. Decision: **25 / 20 / monthly on both universes**, unchanged.

## §3a-c — skip-month, positive-momentum eligibility, trailing stop (14 trials) — IS 2010-2015

Each device alone on the §2 base (vol-adjusted, 25 / 20 / monthly).

| Device | Nifty 250, 12m | NSE 500, 6m |
|---|---|---|
| Base | 19.6% / 0.96 / −22.1%, hit 54% | 24.1% / 1.05 / −28.3%, hit 50% |
| a. skip 5 sessions | 20.5% / 1.00 / −24.8% | 24.8% / 1.11 / −28.7% |
| a. **skip 21 sessions** (12-1 / 6-1) | **20.5% / 1.02 / −21.7%**, hit 57% | **23.6% / 1.06 / −26.6%**, hit 55% |
| b. positive momentum only | 19.7% / 0.97 / −22.1% | 24.1% / 1.05 / −28.3% |
| c. trailing stop 10% | 11.5% / 0.50 / −28.1% | 13.3% / 0.55 / −31.8% |
| c. trailing stop 15% | 17.1% / 0.87 / −27.2% | 16.5% / 0.70 / −32.3% |
| c. trailing stop 20% | 20.9% / 1.09 / −21.9% | 21.7% / 0.96 / −29.0% |
| c. trailing stop 25% | 19.9% / 1.00 / −23.2% | 22.1% / 0.96 / −30.8% |

**Skip-month adopted at 21 sessions**: positive on both universes (+0.06,
+0.01 Sharpe; drawdown and hit rate better on both), the classic
short-term-reversal skip, one rule for both. Positive-only eligibility is
a no-op — the top 25 by vol-adjusted momentum already have positive
momentum. The trailing stop is not adopted: tight stops are destructive
everywhere (10% halves the Sharpe), 20% helps Nifty 250 (+0.13) and hurts
NSE 500 (−0.09), and the Nifty 250 gain is a spike at one width (15%: 0.87,
25%: 1.00). Carried as a walk-forward refit candidate, as in OM25 §4b.

## §3d-e — ROC regime tilt and exposure overlay (72 trials) — IS 2010-2015, on the §3a base

Tilt: bull → absolute momentum, bear → vol-adjusted, regime = NIFTY 100
ROC N ∈ {15, 21, 31, 42} × confirm ∈ {2, 3, 5}. Overlay: the same grid
driving bear exposure to 50% or 0%, entries skipped in bear, re-entry on
the flip.

| | Nifty 250 (base 20.5% / 1.02 / −21.7%) | NSE 500 (base 23.6% / 1.06 / −26.6%) |
|---|---|---|
| d. tilt, best / mean / cells > base | 0.81 / 0.77 / 0 of 12 | 0.84 / 0.69 / 0 of 12 |
| e. overlay 50%, best / mean / cells > base | ROC31/c2: 14.1% / 0.95 / −12.2%; mean 0.76; 0 of 12 | ROC31/c5: 19.0% / 1.08 / −18.2%; mean 0.93; 1 of 12 |
| e. overlay 0%, best / mean / cells > base | 0.74 / 0.50 / 0 of 12 | 0.83 / 0.64 / 0 of 12 |

The tilt is strictly worse — absolute momentum lost to vol-adjusted in
every §1 cell, and switching to it in bull markets imports that loss.
The overlay repeats OM25 §3h: it halves the drawdown and costs 5-8pp of
CAGR on a window with no 2008 in it; one cell edges the base by 0.02 at
−4.6pp CAGR. Neither adopted.

## Standing after §3 — 168 unique trials, in-sample closed

**MM book: vol-adjusted momentum (trailing return / annualised vol,
floor 5%), skip 21 sessions, 25 positions, exit buffer 20, monthly entry
and exit, fully invested, no stop, no overlay. Lookback 12 months on
Nifty 250, 6 months on NSE 500.**

| | Nifty 250 | NSE 500 |
|---|---|---|
| IS 2010-2015 | 20.5% / 1.02 / −21.7% | 23.6% / 1.06 / −26.6% |
| G1 Sharpe ≥ 0.8 raw | pass | pass |
| G8 CAGR ≥ 20% (IS, reported) | pass, barely | pass |

Deflation: 168 trials, observed cross-trial sd 0.18, expected maximum
under the null 0.48; best raw 1.11 → deflated 0.63 (reported, not gated).
Parameters: universe, lookback, skip, top-N, buffer, cadence, vol floor =
7. **OOS not opened.** Awaiting the founder's instruction to open §4 with
both universes, and the same walk-forward design as OM25 §4b.

## §3f — capture-ratio pre-filter (4 trials) — IS 2010-2015, on the §3 base

Founder's reverse of OM25 §5a: keep the top share of names by capture
ratio over the same window, then rank vol-adjusted momentum within them.
`cr_quantile` switch (default off; run ids unchanged).

| Pool by capture ratio | Nifty 250, 12m | NSE 500, 6m |
|---|---|---|
| Whole book (base) | 20.5% / 1.02 / −21.7%, hit 57% | 23.6% / 1.06 / −26.6%, hit 55% |
| Top half | 19.0% / 0.90 / −23.9% | 22.2% / 0.95 / −28.1% |
| Top quartile | 22.5% / 1.16 / −21.3%, hit 58% | 22.7% / 0.96 / −28.9%, hit 51% |

Not adopted. The response is non-monotone — the top half hurts on both
universes and the top quartile helps on one — which is the shape of noise
rather than a mechanism; a filter that works should improve as it
tightens. The one gain (Nifty 250, +0.14) is a single cell on six years.
Carried as a walk-forward refit candidate if the founder wants it counted
there; otherwise closed.

## §3g — other momentum measures and a volume kicker (14 trials) — IS 2010-2015, on the §3 base

Founder's question 2026-09-10. Kinds added to the score: **blend** (mean
percentile rank of vol-adjusted momentum at 3 / 6 / 12 months), **slope**
(annualised exponential-regression slope × R², Clenow), **52-week-high
proximity** (close / window high). Volume kicker: score percentile +
k × percentile of either the **surge** (last 21 sessions' rupee turnover
over the window's) or the **level** (window rupee turnover). Turnover
panel built from the master per-symbol files (`runs/turnover_panel.parquet`).

| Score | Nifty 250, 12m | NSE 500, 6m |
|---|---|---|
| vol-adjusted (base) | **20.5% / 1.02 / −21.7%** | 23.6% / 1.06 / −26.6% |
| absolute | 16.0% / 0.65 / −29.8% | 18.3% / 0.64 / −32.9% |
| blend 3/6/12 | 19.4% / 0.94 / −28.8% | **24.8% / 1.15 / −27.7%** |
| slope × R² | 13.4% / 0.51 / −26.9% | 21.8% / 0.83 / −30.0% |
| 52-week-high proximity | 14.7% / 0.68 / −27.8% (249 trades/yr) | 13.0% / 0.51 / −29.1% (380) |
| + volume surge, k 0.25 / 0.5 | 0.87 / 0.78 | 0.83 / 0.81 |
| + turnover level, k 0.25 / 0.5 | 0.52 / 0.33 | 0.47 / 0.32 |

Nothing beats single-horizon vol-adjusted momentum on both universes.
The blend helps NSE 500 (+0.09) and hurts Nifty 250 (−0.08) — kept as a
walk-forward refit candidate. Slope and 52-week-high are worse
everywhere; the high-proximity score churns (it ranks everything near a
high alike). **Volume does not help as a kicker**: a surge tilt costs
0.15-0.25 of Sharpe, and a turnover-level tilt is destructive (−0.5 to
−0.7) because it drags the book toward the largest names, and on these
universes the momentum premium sits in the smaller ones. Volume may still
have a place as a liquidity floor for capacity, which is a constraint, not
a score; not tested here.

## §4 — OOS, opened once (2026-09-10) — 2016-01-01 → 2026-09-09

Two candidates fixed before any 2016+ statistic: the §3 book on each
universe. One run each from 2010-01-01 to today; IS is the 2010-2015
window of the same path. Walk-forward: yearly refit on trailing 5 and 10
years over kind {abs, voladj, blend} × skip {0, 21} × buffer {10, 20} ×
stop {off, 20%} × capture-ratio top-quartile pre-filter {off, on} = 48
configurations per universe, each run 2006-02-01 → today. 186 unique
in-sample trials preceded the opening.

| Candidate | IS 2010-15 | OOS 2016-26 | Sub-windows 16-19 / 20-22 / 23-26 | Walk-fwd 5y | Walk-fwd 10y | Trades/yr | Gates (static) |
|---|---|---|---|---|---|---|---|
| A N250 monthly 12m | 20.5% / 1.02 | **19.7% / 0.73 / -37.9%** | 0.49 / 1.12 / 0.65 | 19.2% / 0.75 / -37.0% | 20.9% / 0.83 / -38.5% | 87 | G2 fail, G3 fail, G4 pass, G5 pass, G8 fail |
| B N500 monthly 6m | 23.6% / 1.06 | **21.7% / 0.78 / -33.6%** | 0.57 / 1.51 / 0.37 | 17.9% / 0.59 / -39.3% | 17.9% / 0.61 / -37.2% | 181 | G2 fail, G3 fail, G4 pass, G5 pass, G8 pass |

Hindsight-best single configuration on the whole OOS: Nifty 250 —
vol-adjusted, skip 21, buffer 20, **20% stop, capture-ratio pre-filter
on**: 22.8% / 0.98; NSE 500 — the static book itself (0.78; nothing in
the 48 beats it).

Walk-forward picks 2016 → 2026, ten-year window (kind/skip/buffer/stop/CR):
A [(2016, 'blend/21/20/0.2/0.0'), (2017, 'blend/0/10/0.2/0.0'), (2018, 'voladj/21/20/0.2/0.25'), (2019, 'voladj/21/20/0.2/0.25'), (2020, 'voladj/21/20/0.0/0.25'), (2021, 'voladj/21/20/0.2/0.25'), (2022, 'voladj/21/20/0.2/0.25'), (2023, 'voladj/21/20/0.2/0.25'), (2024, 'blend/21/20/0.2/0.25'), (2025, 'voladj/21/20/0.2/0.25'), (2026, 'voladj/21/20/0.2/0.25')]
B [(2016, 'voladj/21/10/0.0/0.0'), (2017, 'blend/0/20/0.2/0.25'), (2018, 'blend/0/20/0.2/0.25'), (2019, 'blend/0/20/0.0/0.25'), (2020, 'voladj/21/20/0.0/0.0'), (2021, 'voladj/21/20/0.0/0.0'), (2022, 'blend/0/20/0.2/0.25'), (2023, 'blend/0/20/0.0/0.25'), (2024, 'voladj/21/20/0.0/0.0'), (2025, 'voladj/21/20/0.0/0.0'), (2026, 'voladj/21/20/0.0/0.0')]

**Both candidates fail G2 (OOS Sharpe 0.73 and 0.78 against 0.9) and G3
(2016-2019 at 0.49 and 0.57; NSE 500 also 2023-26 at 0.37). Both pass G4
and G5. G8: NSE 500 passes (21.7%), Nifty 250 misses by 0.3pp (19.7%; 20.0%
over 2010-26).** The adaptive process helps Nifty 250 (ten-year refit
0.83, adding the stop from 2021 and the capture-ratio filter from 2025)
and hurts NSE 500 (0.59-0.61; the five-year window chases absolute
momentum in 2024-25 and loses). No MM process meets the gates.

Against OM25 on the same windows: OM25's static book did 0.79 / 0.75 and
its adaptive process 0.90; MM's are 0.73 / 0.78 static and 0.83 adaptive.
The momentum book is 0.1-0.3 of Sharpe behind the capture-ratio book
in-sample and out, on both universes, with deeper drawdowns (−34 to −38%
against −35%) and twice the trades on NSE 500. Its one window of clear
strength is 2020-2022 (1.12-1.51), the broad small-cap rally, where it
beats OM25 (0.99-1.29).

## §5 — production L6 v2 on the honest universe, and its structure as devices (12 trials)

L6 v2's exact rules (6-month vol-adjusted momentum, no skip, top 24 with
a 7.5% weight cap, exit buffer 0 with an 8-day minimum hold, weekly
Thursday signal) run through this harness from 2010, both universes. The
spine measured it on the same store as 27.8% / 0.86 / −43.6% from 2020;
this reproduction gives 27.6% / 0.95 / −37% (execution-day mapping and
panel vintage differ).

| L6 v2 rules on | IS 2010-15 | OOS 2016-26 | 16-19 / 20-22 / 23-26 | 2020-26 | Trades/yr |
|---|---|---|---|---|---|
| NSE 500 (production universe) | 17.6% / 0.68 / −31% | 17.4% / 0.56 / −47% | **−0.15** / 1.56 / 0.42 | 27.6% / 0.95 / −37% | 449 |
| Nifty 250 | 12.1% / 0.44 / −35% | 17.6% / 0.64 / −35% | 0.14 / 1.34 / 0.48 | 24.2% / 0.89 / −32% | 404 |
| MM §3 book, NSE 500 (for reference) | 23.6% / 1.06 / −27% | 21.7% / 0.78 / −34% | 0.57 / 1.51 / 0.37 | | 181 |
| MM §3 book, Nifty 250 | 20.5% / 1.02 / −22% | 19.7% / 0.73 / −38% | 0.49 / 1.12 / 0.65 | | 87 |

The production rules lose to the rebuilt book on every window except
2020-2022, with 2016-2019 negative on NSE 500 and two and a half times
the trades. The published 50% from 2020 is the backdated universe; on the
honest one L6 v2 is a 0.56 book over ten years.

L6's structural elements as devices on the MM base, IS 2010-2015
(labelled post-OOS):

| Device | Nifty 250 | NSE 500 |
|---|---|---|
| Base | 20.5% / 1.02 / −21.7% | 23.6% / 1.06 / −26.6% |
| 7.5% weight cap | identical (never binds at 25 names, monthly) | identical |
| 8-day minimum hold, buffer 20 | identical (monthly exits are ≥ 20 days apart) | identical |
| 8-day minimum hold, buffer 0 | 18.9% / 0.90 / −24.2%, 167 trades/yr | 21.0% / 0.91 / −27.7%, 258 |
| Weekly Thursday signal, buffer 20 | 18.8% / 0.90 / −21.1% | 23.7% / 1.04 / −26.2% |
| Full L6 structure with the MM score | 17.6% / 0.81 / −25.5%, 298 | 22.2% / 0.95 / −28.8%, 449 |

Nothing in L6's structure helps: the cap and the minimum hold are no-ops
on a monthly book with a buffer, and the weekly / zero-buffer design that
needs them costs 0.1-0.2 of Sharpe and triples the trades. The cue from
production is negative — the §2 mechanics already superseded it.

## §6 — founder's weekly configuration (4 trials) — labelled post-OOS

6-month momentum, no skip, weekly (Friday signal) rebalance, 8-day
minimum hold, 25 stocks, exit buffer 25, 20% trailing stop. Run
2010 → today; IS and OOS reported together because OOS is open.

| | IS 2010-15 | OOS 2016-26 | 16-19 / 20-22 / 23-26 | 2010-26 | Trades/yr, hit, stop exits |
|---|---|---|---|---|---|
| Nifty 250, vol-adjusted | 16.0% / 0.70 / −32% | 18.8% / 0.71 / −35% | 0.35 / 1.20 / 0.60 | 17.7% / 0.70 / −35% | 186, 47%, 17% |
| Nifty 250, absolute | 10.3% / 0.29 / −37% | 19.7% / 0.70 / −36% | 0.26 / 1.35 / 0.55 | 16.3% / 0.56 / −37% | 191, 47%, 23% |
| NSE 500, vol-adjusted | 23.5% / 1.03 / −29% | 17.5% / 0.58 / −40% | 0.18 / 1.23 / 0.38 | 19.7% / 0.72 / −40% | 239, 46%, 21% |
| NSE 500, absolute | 21.5% / 0.77 / −32% | 19.0% / 0.58 / −46% | 0.14 / 1.27 / 0.44 | 20.0% / 0.65 / −46% | 239, 46%, 31% |
| §3 book, Nifty 250 (monthly, skip 21, buffer 20, no stop) | 20.5% / 1.02 / −22% | 19.7% / 0.73 / −38% | 0.49 / 1.12 / 0.65 | 20.0% | 87, 57% |
| §3 book, NSE 500 | 23.6% / 1.06 / −27% | 21.7% / 0.78 / −34% | 0.57 / 1.51 / 0.37 | 22.4% | 181, 55% |

Below the §3 book on both universes in both windows: −0.3 of Sharpe
in-sample on Nifty 250, −0.2 out-of-sample on NSE 500, with two to three
times the trades and a hit rate under 50%. The pieces behave as they did
individually (§2: weekly and wide buffers add trades without Sharpe; §3c:
the stop helps only Nifty 250 monthly; §5: the minimum hold only matters
when the buffer is gone). Not adopted.

### Wright's window (Oct-2020 → Aug-2026, 71 months; theirs ex-costs, ours net)

| | CAGR | Monthly MaxDD | 2026 YTD | 1Y | 3Y | Vol |
|---|---|---|---|---|---|---|
| Wright Momentum | 31.2% | −21.7% | 8.9% | 14.2% | 18.4% | 20.0% |
| §6 weekly config, Nifty 250 | 25.2% | −18.5% | 0.5% | 8.9% | 17.2% | 20.7% |
| §6 weekly config, NSE 500 | 23.9% | −30.9% | 6.2% | 11.2% | 9.0% | 23.7% |
| §3 book, Nifty 250 | 26.2% | −25.9% | 4.9% | 8.9% | 24.0% | 21.7% |
| §3 book, NSE 500 | 21.1% | −32.6% | −2.9% | 1.6% | 8.0% | 23.4% |
| L6 v2 rules, NSE 500 | 25.2% | −32.0% | 6.5% | 10.8% | 10.5% | 25.0% |
| MidSmall 400 | 23.6% | −22.0% | 3.0% | 8.2% | 14.9% | 18.1% |

On this window the weekly Nifty 250 configuration is the one MM variant
with a Wright-like risk profile (drawdown −18.5%, vol 20.7%), 6pp behind
on return; every NSE 500 variant carries a −31 to −33% drawdown. None of
the MM books beats the MidSmall 400 on risk-adjusted terms here, and the
OM25 adaptive book (26.3% / −26.4%, 3Y 25.4%) remains ahead of all of
them on the trailing three years.

## §7 — capture analysis: is MM getting the upside? (no new trials)

Monthly up- and down-capture against the MidSmall 400 (compound mean
monthly return in the index's up months / down months, portfolio over
index), plus leg returns over the index's actual bull and bear legs.

**Wright's window, Oct-2020 → Aug-2026 (45 up months, 23 down):**

| Book | Up-capture | Down-capture | Beats index in up / down months |
|---|---|---|---|
| MM §3, Nifty 250 | 1.09 | **1.11** | 51% / 52% |
| MM §3, NSE 500 | 1.09 | **1.37** | 58% / 35% |
| MM weekly §6, Nifty 250 | 1.08 | 1.07 | 53% / 48% |
| L6 v2 rules, NSE 500 | 1.13 | 1.24 | 56% / 48% |
| OM25 adaptive, Nifty 250 | 1.05 | 0.97 | 49% / 57% |
| Wright (ex-costs) | 1.11 | **0.90** | 62% / 57% |

**Leg returns, %:**

| Book | Bull Apr-20 → Oct-21 | Bear Oct-21 → Jun-22 | Bull Jun-22 → Sep-24 | Bear Sep-24 → Feb-25 | Bull Feb-25 → Aug-26 | Calendar 2021 |
|---|---|---|---|---|---|---|
| MidSmall 400 | 132.0 | −12.4 | 124.3 | −22.0 | 27.4 | 51.3 |
| MM §3, Nifty 250 | 105.7 | 0.6 | 124.2 | −25.4 | 37.8 | 56.8 |
| MM §3, NSE 500 | 157.7 | −5.0 | 142.8 | −28.6 | 8.8 | 69.7 |
| MM weekly §6, Nifty 250 | 143.1 | −14.6 | 131.4 | −18.4 | 17.6 | 63.2 |
| L6 v2 rules, NSE 500 | 206.0 | −6.8 | 125.4 | −27.0 | 18.7 | 97.7 |
| OM25 adaptive, Nifty 250 | 99.3 | −8.4 | 136.3 | −25.4 | 48.9 | 57.5 |
| Wright | 104.1 | −3.4 | 143.8 | −20.5 | 30.2 | 91.4 |

**Long run 2011 → today vs MidSmall 400:** MM §3 Nifty 250 0.94 up /
0.66 down; NSE 500 1.08 / 0.80; OM25 adaptive 0.88 / 0.51. Vs NIFTY 500:
MM Nifty 250 1.19 / 0.81, NSE 500 1.29 / 0.85, OM25 1.10 / 0.61.

Read:
1. **The upside is there.** Every MM variant captures 1.08-1.13 of the
   index's up months on this window, the same as Wright's 1.11; over the
   long run MM captures 1.2-1.3 of NIFTY 500's up months.
2. **The problem is entirely the down months.** MM gives back 1.07-1.37
   of the index's down months; Wright gives back 0.90, OM25 0.97. That
   0.2-0.5 gap in down-capture is the whole difference in Sharpe. On the
   long run MM's down-capture is fine (0.66-0.85); it is the 2022 and
   Sep-24 → Feb-25 momentum unwinds that hurt — the book holds the
   highest-beta leaders into the turn.
3. **Wright's 91% is not bull-leg over-capture.** Over the full Apr-20 →
   Oct-21 leg they made 104% against the index's 132% — less than the
   index and less than every MM book. Their 2021 is timing inside the
   leg (they lagged Oct-Dec 2020, 15.9% vs 21.4%). Where they actually
   win is the two bears (−3.4 vs −12.4, −20.5 vs −22.0) and the 2022-24
   bull (144 vs 124).
4. L6 v2's rules made 206% on the first leg and 98% in 2021 — the weekly,
   zero-buffer book is the best bull-leg capturer here — and gave it back
   in both bears; that is the production story from 2020 in one row.

The lever for MM is bear-month behaviour, not the score. Candidate
devices, all previously tested only on 2010-2015: the 20% stop (§6 weekly
already shows 1.07 vs 1.11), the ROC exposure overlay, and the 200-DMA
breadth overlay from OM25 §3j. Any test now is post-OOS by construction
and must be judged on both legs — the cost in the bull legs against the
saving in the bears.

## §8 — bear-month behaviour: every exposure device, judged by leg (26 trials) — post-OOS by construction

Devices on the §3 base, both universes, runs 2010 → today. Regime for
the ROC devices NIFTY 100 ROC31 / confirm 3; breadth = share of members
above their 200-DMA < 30%, confirm 3; both confirmed then lagged one
session. **Dynamic count** (founder): 25 names in bull, N in bear —
"lever" keeps each name at 1/25 so gross exposure falls to N/25;
"concentrate" lets the engine's 1/n sizing keep the book fully invested
in N names. **Vol target**: exposure = min(1, target / trailing 21-day
NIFTY 500 vol), set at Friday's close, applied from the next session.
Look-ahead checked by rebuilding each series from data truncated the
day before (`phase8` preamble; both checks pass). Capture = compound
mean monthly return in the MidSmall 400's up / down months, over the
index's. Legs in %, MidSmall 400: 132 / −12 / 124 / −22 / 27.

**Nifty 250, 12m**
| Device | IS Sharpe | OOS 2016-26 | Wright window | Up / down capture (Wright window) | Up / down (2011-26) | Legs: bull20-21 / bear21-22 / bull22-24 / bear24-25 / bull25-26 | Avg exposure |
|---|---|---|---|---|---|---|---|
| base | 1.02 | 19.7% / 0.73 / -38% | 26.2% / 1.03 / -30% | 1.09 / 1.11 | 0.94 / 0.66 | 106 / 1 / 124 / -25 / 38 | 99% |
| stop 20% | 1.04 | 20.1% / 0.83 / -30% | 29.0% / 1.23 / -26% | 1.10 / 0.99 | 0.90 / 0.59 | 108 / -3 / 154 / -24 / 35 | 96% |
| ROC overlay 50% | 0.89 | 14.5% / 0.76 / -19% | 19.1% / 1.04 / -19% | 0.67 / 0.47 | 0.58 / 0.32 | 68 / -5 / 124 / -15 / 7 | 66% |
| ROC overlay 0% | 0.73 | 16.7% / 0.86 / -23% | 16.5% / 0.77 / -23% | 0.60 / 0.42 | 0.54 / 0.20 | 82 / -14 / 98 / -10 / 4 | 65% |
| breadth overlay 50% | 1.06 | 16.1% / 0.66 / -30% | 23.7% / 1.04 / -20% | 0.92 / 0.86 | 0.78 / 0.52 | 84 / -4 / 131 / -19 / 16 | 87% |
| breadth overlay 0% | 0.95 | 15.7% / 0.63 / -25% | 22.6% / 0.97 / -23% | 0.86 / 0.78 | 0.72 / 0.47 | 89 / -12 / 136 / -13 / 8 | 88% |
| dyn N 18 lever (ROC) | 0.83 | 15.6% / 0.75 / -28% | 23.2% / 1.22 / -16% | 0.74 / 0.43 | 0.61 / 0.34 | 75 / -3 / 117 / -9 / 19 | 71% |
| dyn N 15 lever (ROC) | 0.81 | 14.8% / 0.77 / -21% | 21.1% / 1.17 / -15% | 0.67 / 0.38 | 0.56 / 0.28 | 71 / -5 / 105 / -7 / 15 | 64% |
| dyn N 15 concentrate (ROC) | 0.99 | 21.7% / 0.85 / -38% | 32.1% / 1.35 / -27% | 1.09 / 0.80 | 0.92 / 0.58 | 122 / 9 / 145 / -26 / 42 | 96% |
| dyn N 15 lever (breadth) | 1.08 | 16.7% / 0.68 / -32% | 24.5% / 1.08 / -20% | 0.92 / 0.79 | 0.78 / 0.50 | 97 / -1 / 129 / -18 / 13 | 89% |
| vol target 20% | 0.89 | 16.4% / 0.64 / -29% | 23.3% / 0.98 / -25% | 0.99 / 1.02 | 0.83 / 0.60 | 84 / -3 / 130 / -24 / 25 | 91% |
| vol target 15% | 0.88 | 14.7% / 0.62 / -24% | 21.4% / 0.99 / -23% | 0.85 / 0.78 | 0.71 / 0.49 | 61 / 3 / 121 / -23 / 19 | 82% |
| vol target 15% + stop 20% | 0.86 | 14.2% / 0.61 / -22% | 21.3% / 1.01 / -22% | 0.84 / 0.76 | 0.66 / 0.43 | 58 / 5 / 119 / -20 / 15 | 80% |

**NSE 500, 6m**
| Device | IS Sharpe | OOS 2016-26 | Wright window | Up / down capture (Wright window) | Up / down (2011-26) | Legs: bull20-21 / bear21-22 / bull22-24 / bear24-25 / bull25-26 | Avg exposure |
|---|---|---|---|---|---|---|---|
| base | 1.06 | 21.7% / 0.78 / -34% | 21.1% / 0.74 / -34% | 1.09 / 1.37 | 1.08 / 0.80 | 158 / -5 / 143 / -29 / 9 | 99% |
| stop 20% | 0.90 | 17.7% / 0.63 / -35% | 20.3% / 0.74 / -35% | 1.05 / 1.34 | 1.01 / 0.83 | 158 / -3 / 124 / -29 / 7 | 96% |
| ROC overlay 50% | 0.92 | 18.5% / 0.92 / -20% | 15.6% / 0.69 / -20% | 0.71 / 0.79 | 0.73 / 0.45 | 113 / -7 / 95 / -14 / -1 | 70% |
| ROC overlay 0% | 0.63 | 16.7% / 0.80 / -25% | 11.9% / 0.44 / -25% | 0.57 / 0.66 | 0.61 / 0.34 | 110 / -16 / 77 / -7 / -8 | 65% |
| breadth overlay 50% | 0.95 | 17.0% / 0.64 / -33% | 20.2% / 0.77 / -33% | 0.99 / 1.21 | 0.88 / 0.68 | 132 / -2 / 124 / -24 / -1 | 87% |
| breadth overlay 0% | 0.87 | 15.8% / 0.59 / -33% | 19.7% / 0.75 / -33% | 0.94 / 1.12 | 0.83 / 0.65 | 120 / -1 / 122 / -21 / -7 | 84% |
| dyn N 18 lever (ROC) | 0.91 | 17.2% / 0.81 / -25% | 18.5% / 0.86 / -25% | 0.72 / 0.65 | 0.69 / 0.41 | 140 / -6 / 75 / -4 / 1 | 68% |
| dyn N 15 lever (ROC) | 0.83 | 16.8% / 0.82 / -23% | 18.1% / 0.86 / -23% | 0.69 / 0.61 | 0.64 / 0.37 | 136 / -5 / 68 / -3 / 1 | 64% |
| dyn N 15 concentrate (ROC) | 0.98 | 19.7% / 0.70 / -35% | 19.9% / 0.70 / -29% | 1.01 / 1.29 | 1.03 / 0.81 | 142 / -6 / 125 / -25 / 12 | 95% |
| dyn N 15 lever (breadth) | 0.85 | 15.3% / 0.55 / -33% | 18.5% / 0.68 / -33% | 0.94 / 1.20 | 0.84 / 0.68 | 130 / -0 / 110 / -23 / -5 | 85% |
| vol target 20% | 1.04 | 17.8% / 0.65 / -34% | 19.1% / 0.70 / -34% | 1.02 / 1.31 | 0.97 / 0.74 | 123 / -8 / 133 / -28 / 4 | 91% |
| vol target 15% | 0.83 | 17.7% / 0.72 / -28% | 20.8% / 0.90 / -28% | 0.89 / 0.92 | 0.80 / 0.58 | 101 / 9 / 100 / -26 / 7 | 80% |
| vol target 15% + stop 20% | 0.73 | 15.8% / 0.65 / -28% | 20.6% / 0.93 / -28% | 0.86 / 0.87 | 0.74 / 0.56 | 102 / 14 / 89 / -24 / 4 | 77% |

Read, Nifty 250:
1. **Two devices cut down-capture without touching up-capture.** The 20%
   stop: down 1.11 → 0.99, up unchanged, OOS 0.73 → 0.83, drawdown −38 →
   −30, better on two of three bull legs. **Concentrating to 15 names in
   bear** (fully invested): down 1.11 → 0.80, up 1.09 unchanged, OOS 0.85,
   Wright-window 32.1% / 1.35 / −27%, and it wins every bull leg and the
   2021-22 bear (+8.7 against the index's −12). In a bear the top 15 by
   vol-adjusted momentum are the resilient leaders; ranks 16-25 are what
   falls. It does nothing for the Sep-24 → Feb-25 unwind (−26).
2. Every device that cuts *exposure* — ROC overlay, lever-down count,
   vol targeting — cuts up-capture by as much as or more than
   down-capture (up 0.60-0.85 against down 0.38-0.78) and loses 3-10pp of
   CAGR on Wright's window. The lever-down count is the least bad of
   them (Wright-window Sharpe 1.17-1.22, drawdown −15%) at 21-23% CAGR.
3. Vol targeting on index vol does not help a stock-momentum book here:
   up and down capture fall together.

Read, NSE 500: nothing preserves the upside. The ROC 50% overlay is the
one device that lifts OOS Sharpe above 0.9 (0.92, drawdown −20%) and it
costs 5-6pp of CAGR on Wright's window (bull legs 113 / 95 / −1 against
158 / 143 / 9). Concentration does not help on this universe (down 1.29).
The NSE 500 book's bear problem is the universe's beta, not its tail.

The Sep-24 → Feb-25 unwind (index −22) is not fixed by any device that
keeps the upside; only the lever-down and ROC-exit variants avoid it
(−3 to −10), by not being invested.

Caveats: post-OOS; 13 devices × 2 universes looked at; the two Nifty 250
winners are single cells until §8b checks their neighbours (N ∈ {12, 15,
18, 20}, two ROC lengths, breadth regime, with and without the stop).

## §8b — robustness of concentrate-in-bear (44 trials) — post-OOS

Nifty 250: N in bear ∈ {12, 15, 18, 20} × regime ∈ {ROC31, ROC21, ROC42
(confirm 3), breadth 200-DMA < 30%} × stop ∈ {off, 20%}. OOS Sharpe
2016-26 (base 0.73):

| N in bear | ROC31/c3 no stop / stop | ROC21/c3 no stop / stop | ROC42/c3 no stop / stop | breadth200<30% no stop / stop |
|---|---|---|---|---|
| 12 | 0.83 / **0.93** | 0.83 / **0.88** | 0.77 / **0.86** | 0.88 / **0.95** |
| 15 | 0.85 / **0.93** | 0.83 / **0.87** | 0.79 / **0.84** | 0.85 / **0.91** |
| 18 | 0.79 / **0.87** | 0.79 / **0.83** | 0.74 / **0.82** | 0.81 / **0.87** |
| 20 | 0.79 / **0.89** | 0.80 / **0.85** | 0.72 / **0.83** | 0.80 / **0.87** |

It is a plateau, not a spike: with the stop every one of the 16 cells is
0.82-0.95, and 12-15 names in bear with ROC31 or breadth is the flat top.
The stop adds 0.07-0.10 everywhere (its work is the 2020 crash: drawdown
−38% → −28%); the regime choice matters little (ROC42 is the slow one).

| Cell | IS | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Wright window | Up / down capture |
|---|---|---|---|---|---|
| N 12, breadth200<30%, stop 20% | 0.96 | 22.0% / 0.95 / -30% | 0.47 / 1.30 / 1.13 | 31.5% / 1.40 / -25% | 1.11 / 0.84 |
| N 15, ROC31/c3, stop 20% | 1.06 | 21.8% / 0.93 / -28% | 0.34 / 1.59 / 0.95 | 32.1% / 1.41 / -27% | 1.10 / 0.84 |
| N 12, ROC31/c3, stop 20% | 0.98 | 21.8% / 0.93 / -28% | 0.37 / 1.55 / 0.95 | 31.4% / 1.37 / -27% | 1.10 / 0.86 |
| N 15, breadth200<30%, stop 20% | 1.06 | 21.3% / 0.91 / -30% | 0.41 / 1.29 / 1.08 | 31.0% / 1.37 / -25% | 1.09 / 0.84 |

Every cell in that top group passes G2 (≥ 0.9), G4 (−28 to −30%) and G8
(21-22%), and every cell fails G3 on 2016-2019 (0.3-0.5) — the window
before any bear device matters, where momentum on Nifty 250 was simply
weak (the §3 base does 0.49 there too). Capture on Wright's window 1.09-1.11
up / 0.80-0.86 down, against Wright's 1.11 / 0.90; return 31-32% against
their 31.2% (theirs gross), drawdown −27% against −22%.

NSE 500 (12 cells): no help — down-capture stays 1.10-1.35, OOS
0.65-0.79. Concentration removes a bad tail; NSE 500's problem is the
whole book's beta.

Caveats: post-OOS design, 70 cells looked at in §8-8b; the 2024-25
unwind is unchanged (−25 to −27 in every cell); N and the regime were
searched on the same window they are judged on. What is not in doubt is
the mechanism's sign across a 4 × 4 × 2 grid.

## §9 — Wright-review hypotheses 1 and 2 (11 trials) — post-OOS

From `WRIGHT_REVIEW.md`: (1) their universe is "the top 300" with a
traded-volume minimum, not NSE 500; (2) their one printed sizing rule is
mean-variance weights with a 10% name cap. Tested as: a point-in-time
top-300 (Nifty 250 members plus the 50 most liquid others by trailing
rupee turnover), rupee-turnover floors of 2 and 5 crore a day (median
over the window), and inverse-volatility sizing (63-day, weights
proportional to 1/vol over the intended book, capped at 10%, existing
positions drift as in the equal-weight engine). Sizing runs through a
copy of the engine with one additive hook (`lib/_engine_iv.py`);
byte-identity with the production engine at equal weight is verified in
`phase9`. No sector cap: the store has no sector data. Vol for sizing
uses returns to the signal date; the entry executes the next session.

| Cell | IS Sharpe | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Wright window | Up / down capture | Legs | Trades/yr |
|---|---|---|---|---|---|---|---|
| N500 base | 1.06 | 21.7% / 0.78 / -34% | 0.57 / 1.51 / 0.37 | 21.1% / 0.74 / -34% | 1.09 / 1.37 | 158 / -5 / 143 / -29 / 9 | 175 |
| N500 floor 2cr/day | 0.56 | 22.0% / 0.79 / -34% | 0.62 / 1.50 / 0.37 | 20.9% / 0.73 / -34% | 1.08 / 1.37 | 158 / -5 / 143 / -29 / 9 | 170 |
| N500 floor 5cr/day | 0.26 | 19.8% / 0.68 / -34% | 0.40 / 1.40 / 0.37 | 21.3% / 0.76 / -33% | 1.09 / 1.36 | 153 / -10 / 140 / -29 / 11 | 158 |
| top-300 (6m) | 0.72 | 17.5% / 0.60 / -36% | 0.13 / 1.28 / 0.47 | 22.3% / 0.81 / -29% | 1.11 / 1.32 | 149 / -11 / 135 / -28 / 16 | 157 |
| top-300 (12m) | 0.54 | 20.2% / 0.71 / -45% | 0.17 / 0.91 / 1.07 | 30.2% / 1.14 / -30% | 1.17 / 1.11 | 116 / -8 / 165 / -27 / 54 | 90 |
| top-300 + floor 2cr | 0.61 | 18.5% / 0.63 / -37% | 0.26 / 1.27 / 0.47 | 21.8% / 0.79 / -29% | 1.09 / 1.32 | 149 / -11 / 135 / -28 / 16 | 157 |
| N500 inv-vol cap 10% | 1.11 | 22.0% / 0.86 / -30% | 0.67 / 1.61 / 0.42 | 22.3% / 0.85 / -30% | 1.07 / 1.29 | 149 / -5 / 136 / -27 / 12 | 176 |
| N500 inv-vol cap 10% + floor 2cr | 0.52 | 21.6% / 0.83 / -30% | 0.67 / 1.53 / 0.42 | 21.8% / 0.83 / -30% | 1.06 / 1.28 | 139 / -5 / 136 / -27 / 12 | 170 |
| top-300 inv-vol cap 10% | 0.72 | 18.2% / 0.68 / -33% | 0.21 / 1.52 / 0.40 | 23.3% / 0.91 / -29% | 1.07 / 1.21 | 150 / -8 / 128 / -28 / 16 | 157 |
| N250 base | 1.02 | 19.7% / 0.73 / -38% | 0.49 / 1.12 / 0.65 | 26.2% / 1.03 / -30% | 1.09 / 1.11 | 106 / 1 / 124 / -25 / 38 | 84 |
| N250 inv-vol cap 10% | 1.14 | 19.3% / 0.78 / -34% | 0.55 / 1.12 / 0.71 | 25.0% / 1.05 / -26% | 1.01 / 0.99 | 99 / -3 / 131 / -25 / 34 | 83 |
| N250 inv-vol cap 10% + concentrate 15 + stop | 1.18 | 21.0% / 0.95 / -26% | 0.40 / 1.48 / 1.04 | 30.2% / 1.42 / -26% | 1.03 / 0.77 | 112 / -2 / 147 / -25 / 39 | 135 |

Read:
1. **Universe is not the lever on NSE 500.** Turnover floors change
   nothing (down-capture 1.36-1.37). Cutting to a top-300 at 6 months
   loses OOS Sharpe (0.60) and keeps the down-capture (1.32); at 12
   months it reproduces the Nifty 250 profile (down 1.11) with a −45%
   OOS drawdown. The small-cap tail is where the upside lives too —
   removing it removes both.
2. **Inverse-vol sizing is the one device that improves NSE 500 while
   keeping the upside**: OOS 0.78 → 0.86, drawdown −34 → −30, down-capture
   1.37 → 1.29 with up-capture 1.07. Still short of G2, and the down
   months stay above the index's.
3. On Nifty 250, inverse-vol brings down-capture to 0.99 alone and, on top
   of §8b's concentrate-15 + stop, to **0.77 with up-capture 1.03: OOS
   21.0% / 0.95 / −26%, Wright window 30.2% / 1.42 / −26%, IS 1.18** — the
   best MM cell on every risk measure, at a cost of 0.8pp of OOS CAGR
   against the equal-weight version (21.8% / 0.93 / −28%).

Net: Wright's structure, to the extent the pages reveal it, does not
unlock NSE 500. Their universe is closer to our Nifty 250 book, and the
sizing rule they printed helps our Nifty 250 book the way it should.

## §9b — audit of the "concentrate" mechanism, and the founder's idea implemented properly (7 trials)

**Correction to §8, §8b and §9.** Counting holdings on bear dates showed
the runs labelled "concentrate 15" did not hold 15 names: the score list
was cut to 15 + buffer = 35 in bear, but the engine still filled the book
toward 25 from the top of that list, so what actually ran was **a
tighter exit rank in bear (35 instead of 45)** with the book drifting to
17-25 names (mean 20, 86-88% invested). The numbers stand; the label was
wrong. Those cells are relabelled "tight exit in bear" here.

The founder's idea — hold fewer names in bear, fully invested — needs a
per-rebalance top-N, which the engine did not have. Added to the engine
copy as an additive `top_n_fn` hook (entries capped at N in bear; exits
at rank N + bear buffer through the truncated list). One limit remains:
the engine never resizes an existing position, so names bought at 1/25
in bull are not topped up to 1/15 in bear and the bear book carries some
cash — reported as "invested". Nifty 250, 12m, skip 21, monthly, 20% stop;
regime NIFTY 100 ROC31 / confirm 3, lagged.

| Cell | IS | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Wright window | Up / down | Bear book | Trades/yr |
|---|---|---|---|---|---|---|---|
| A as run: bear exit rank 35 (tight exit), equal, stop | 1.06 | 21.8% / 0.93 / -28% | 0.34 / 1.59 / 0.95 | 32.1% / 1.41 / -27% | 1.10 / 0.84 | 20 names, 88% | 135 |
| B as run + inv-vol 10% | 1.18 | 21.0% / 0.95 / -26% | 0.40 / 1.48 / 1.04 | 30.2% / 1.42 / -26% | 1.03 / 0.77 | 20 names, 86% | 135 |
| C hold<=15 in bear, bear buffer 10, equal, stop | 0.84 | 25.0% / 0.86 / -24% | 0.21 / 2.17 / 0.45 | 40.2% / 1.29 / -23% | 1.03 / 0.24 | 12 names, 58% | 113 |
| D hold<=15 in bear, bear buffer 20, equal, stop | 0.98 | 22.2% / 0.98 / -28% | 0.47 / 1.61 / 0.96 | 29.7% / 1.30 / -28% | 1.05 / 0.84 | 17 names, 78% | 116 |
| E hold<=15, bear buffer 10, inv-vol 10%, stop | 0.95 | 21.6% / 1.02 / -28% | 0.49 / 1.61 / 1.02 | 28.1% / 1.30 / -28% | 0.98 / 0.75 | 15 names, 75% | 126 |
| F hold<=18, bear buffer 10, inv-vol 10%, stop | 1.06 | 21.2% / 0.98 / -28% | 0.40 / 1.60 / 1.02 | 29.0% / 1.34 / -28% | 1.03 / 0.83 | 17 names, 80% | 127 |
| G hold<=15, bear buffer 20, inv-vol 10%, stop | 1.14 | 21.9% / 1.03 / -27% | 0.50 / 1.66 / 1.01 | 29.1% / 1.35 / -27% | 1.01 / 0.78 | 17 names, 77% | 116 |

**G — hold ≤ 15 in bear, bear buffer 20, inverse-vol 10% cap, 20% stop —
is the best MM cell: OOS 21.9% / 1.03 / −27%, sub-windows 0.50 / 1.66 /
1.01, IS 1.14, down-capture 0.78 with up-capture 1.01.** Passes G2, G4,
G8; G3 fails on 2016-19 at 0.50, the closest any MM cell has come.

## §9c — robustness of hold-N-in-bear (16 trials)

N ∈ {12, 15, 18, 20} × bear buffer ∈ {10, 20} × regime ∈ {ROC31,
breadth}, inverse-vol 10%, stop 20%. OOS Sharpe (base 0.73):

| N in bear | ROC31 bb10 | ROC31 bb20 | breadth bb10 | breadth bb20 |
|---|---|---|---|---|
| 12 | 0.91 | 0.88 | 0.92 | 0.90 |
| 15 | 1.02 | 1.03 | 1.03 | 0.97 |
| 18 | 0.98 | 0.98 | 0.95 | 0.92 |
| 20 | 0.95 | 0.97 | 0.94 | 0.88 |

A plateau with its top at N = 15 (1.02-1.03 on three of four regime ×
buffer settings); every cell is 0.88 or better. The regime choice and
the bear buffer matter less than N.

Trial count post-OOS across §8-§9c: 120 cells. The mechanism's sign is
not in doubt; the exact N is the searched value.

## §9d — sector cap (8 trials) — post-OOS

Sector data: NSE's own Industry labels from 26 archived constituent
lists (`sector/`, 87% of all-ever members; three schemes over time mapped
to the current 21 sectors in `sector/scheme_map.csv`; 13% of names,
mostly pre-2007 or in archive gaps, are unlabelled and unconstrained —
1% of the book's buys). Cap = maximum names per sector at entry (a name
whose sector is full is skipped; holdings are never sold for the cap),
via an additive `sector_cap` hook in the engine copy. Uncapped, the
Nifty 250 book's buys were 18% Financial Services and 12% Healthcare.

| Cell | IS | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Wright window | Up / down |
|---|---|---|---|---|---|
| N250 G (no sector cap) | 1.14 | 21.9% / 1.03 / -27% | 0.50 / 1.66 / 1.01 | 29.1% / 1.35 / -27% | 1.01 / 0.78 |
| N250 G + sector cap 4 (16%) | 1.06 | 24.2% / 1.15 / -26% | 0.73 / 1.74 / 1.07 | 30.5% / 1.36 / -26% | 1.02 / 0.73 |
| N250 G + sector cap 5 (20%) | 1.09 | 24.5% / 1.17 / -26% | 0.61 / 1.81 / 1.18 | 32.5% / 1.49 / -26% | 1.08 / 0.76 |
| N250 G + sector cap 6 (24%) | 1.13 | 23.8% / 1.12 / -27% | 0.63 / 1.70 / 1.12 | 31.1% / 1.40 / -27% | 1.05 / 0.78 |
| N500 inv-vol (no cap) | 1.11 | 22.0% / 0.86 / -30% | 0.67 / 1.61 / 0.42 | 22.3% / 0.85 / -30% | 1.07 / 1.29 |
| N500 inv-vol + sector cap 4 | 1.06 | 19.7% / 0.76 / -34% | 0.54 / 1.50 / 0.33 | 20.7% / 0.81 / -31% | 1.01 / 1.23 |
| N500 inv-vol + sector cap 6 | 1.09 | 20.4% / 0.79 / -33% | 0.54 / 1.51 / 0.41 | 21.7% / 0.84 / -30% | 1.02 / 1.21 |
| N500 base + sector cap 4 | 0.96 | 19.3% / 0.69 / -35% | 0.45 / 1.42 / 0.28 | 19.0% / 0.68 / -34% | 1.02 / 1.33 |

**On Nifty 250 the sector cap is the missing piece.** With 4-6 names per
sector on top of §9b's cell G the book lifts to OOS 1.12-1.17 and, for the
first time, clears 2016-2019 (0.61-0.73), so **G + cap 5 passes every
gate: G2 1.17, G3 0.61 / 1.81 / 1.18, G4 −26%, G8 24.5%**; on Wright's
window 32.5% / 1.49 / −26% with up-capture 1.08 and down-capture 0.76,
against their 31.2% / 1.11 / 0.90. A plateau across the three caps
(1.12-1.17). The mechanism is the one Wright printed: limiting a
momentum book's habit of stacking one sector at the top of a cycle,
which is where 2016-19 (financials) hurt.

On NSE 500 the cap costs 0.07-0.10 of Sharpe: the momentum there is
sector-concentrated by nature and the cap trades it for lower-ranked
names in other sectors.

Trial count post-OOS §8-§9d: 128 cells. This is now a fully post-OOS
design on Nifty 250; the evidence for each element is a plateau, not a
cell, but the stack as a whole has never been judged on unseen data.

## §10 — followability: rebalance cadence × stop-check cadence (9 trials) — post-OOS

Founder's concern 2026-09-10: monthly rebalancing may be too inactive to
keep subscribers engaged, and a daily exit check too active to follow.
Audit first: **the stop was never checked daily.** The engine tracks each
position's peak daily but tests the stop only at the weekly signal
(Friday close) and sells the next session — 187 of the MM stack's 196
stop exits fall on a Monday. The stop-check cadence is now a parameter
(`stop_check`) in both harnesses. Cells: rebalance ∈ {monthly, biweekly,
weekly} × stop check ∈ {weekly, biweekly, monthly}. Followability =
distinct trading days with any order per month (2016-26), months with
any order, median hold, share of exits by stop. OM25's row is its
current adaptive pick (50/50, buffer 10, stop 20%) run as a fixed
configuration, not the chained process.

| Book | Rebalance / stop check | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Wright window | Up / down | Trades/yr | Action days/month | Median hold | Stop exits |
|---|---|---|---|---|---|---|---|---|---|
| MM stack N250 | monthly / weekly | 24.5% / 1.17 / -26% | 0.61 / 1.81 / 1.18 | 32.5% / 1.49 | 1.08 / 0.76 | 124 | 1.9 (max 6) | 91 | 29% |
| MM stack N250 | monthly / biweekly | 24.3% / 1.16 / -27% | 0.68 / 1.79 / 1.10 | 32.1% / 1.46 | 1.07 / 0.75 | 121 | 1.7 (max 4) | 92 | 26% |
| MM stack N250 | monthly / monthly | 25.7% / 1.18 / -26% | 0.71 / 1.73 / 1.18 | 33.9% / 1.50 | 1.09 / 0.73 | 118 | 1.0 (max 1) | 92 | 23% |
| MM stack N250 | biweekly / weekly | 21.8% / 0.98 / -27% | 0.59 / 1.27 / 1.10 | 28.2% / 1.28 | 1.01 / 0.81 | 155 | 2.6 (max 5) | 70 | 25% |
| MM stack N250 | biweekly / biweekly | 22.6% / 1.02 / -27% | 0.65 / 1.29 / 1.14 | 29.6% / 1.34 | 1.04 / 0.81 | 153 | 2.0 (max 3) | 70 | 22% |
| MM stack N250 | weekly / weekly | 23.2% / 1.02 / -28% | 0.70 / 1.33 / 1.07 | 29.5% / 1.28 | 1.04 / 0.81 | 182 | 3.5 (max 5) | 56 | 20% |
| OM25 current pick N250 | monthly / weekly | 22.2% / 0.82 / -36% | 0.20 / 1.31 / 1.03 | 34.9% / 1.34 | 1.32 / 1.14 | 138 | 2.2 (max 6) | 91 | 40% |
| OM25 current pick N250 | monthly / biweekly | 21.9% / 0.79 / -37% | 0.23 / 1.33 / 0.91 | 34.1% / 1.29 | 1.29 / 1.12 | 132 | 1.8 (max 4) | 92 | 36% |
| OM25 current pick N250 | biweekly / weekly | 20.7% / 0.71 / -44% | 0.15 / 1.11 / 0.90 | 34.4% / 1.26 | 1.33 / 1.20 | 166 | 2.7 (max 5) | 70 | 33% |
| OM25 current pick N250 | biweekly / biweekly | 21.5% / 0.73 / -45% | 0.19 / 1.12 / 0.92 | 35.4% / 1.29 | 1.34 / 1.16 | 160 | 2.1 (max 3) | 70 | 31% |

Read:
1. **The simplest rhythm is also the best.** MM with everything on one day
   a month — rebalance and stop check together on the first trading day —
   is the top cell: 25.7% / 1.18 / −26%, every sub-window ≥ 0.71, and
   exactly one action day per month, never more. Checking the stop weekly
   or biweekly adds nothing (1.16-1.17) and adds action days.
2. **Faster rebalancing costs performance on both books**: biweekly takes
   MM from 1.17 to 0.98-1.02 and OM25 from 0.82 to 0.71-0.73 with the
   drawdown from −36% to −44%; weekly MM is 1.02 at 3.5 action days a
   month. Same non-lever as OM25 §3i and MM §2, now with the stop in.
3. Engagement is therefore a product question, not a strategy one: the
   book wants one order day a month. A weekly review that reports
   rankings, distance to stops and regime state without trading is the
   followable way to be present between rebalances.

Adopted for MM: **monthly rebalance with the stop checked at the same
monthly signal**, one action day. Recommended for OM25 likewise.

## §11 — G5 walk-forward for the adopted stack (32 trials) — post-OOS

G5 asks whether a process that refits the stack's **post-OOS** choices each
January, seeing only trailing data, lands within 0.2 Sharpe of the static
pick. Refit grid: `dyn_n_bear` {12,15,18,20} × `bear_buffer` {10,20} ×
`sector_cap` {0,4,5,6} = 32 cells. Everything decided in-sample (universe,
score, lookback, skip, top-N, buffer, cadence) and everything structural
(monthly stop check, 20% stop, inverse-vol 10%, ROC31/c3) held fixed.

| | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Gap vs static | Config changes |
|---|---|---|---|---|
| Static (the adopted cell) | 25.7% / **1.18** / −26% | 0.71 / 1.73 / 1.18 | — | — |
| Walk-forward, trailing 5y | 22.4% / **0.98** / −29% | 0.66 / 1.15 / 1.14 | **0.200** | 5 |
| Walk-forward, trailing 3y | 22.0% / **0.97** / −29% | 0.55 / 1.31 / 1.07 | **0.215** | 8 |

**G5 is met on the 5-year refit at exactly the threshold (0.200) and missed
on the 3-year refit (0.215).** Calling that a pass would be reading a gate to
three decimals; the honest statement is that the stack sits on the line.

The more informative number is the cross-section. **The adopted cell is rank
1 of all 32** on OOS Sharpe; the grid runs 0.88 to 1.18 with median 1.04 and
standard deviation 0.071. The walk-forward result (0.97-0.98) sits just below
the grid median — which is what selecting without hindsight should produce.

Deflating the OOS Sharpe for the post-OOS search (Bailey-López de Prado, with
the observed cross-trial Sharpe variance of 0.041):

| Deflated against | Deflated Sharpe |
|---|---|
| the 32 cells of this refit grid | 0.76 |
| the ~128 post-OOS cells of §8-§10 | 0.66 |
| all 345 registered MM trials | 0.59 |

**So the stack's realistic expectation is a band, not 1.18:** 1.18 is the
selection-window maximum, 1.04 the plateau centre, 0.98 what a hindsight-free
process delivered, and 0.6-0.8 what deflation implies. For planning, the
walk-forward number is the one to use — roughly **22% CAGR at Sharpe ~1.0**.

## §12 — Wright's Sharpe, the last three years, and the medium-term hold (no new trials)

### Wright Momentum's Sharpe

Computed from their printed month-on-month grid (M-PDF p2, 71 months
Oct-2020 → Aug-2026), with every row on the same basis: monthly returns,
rf 5%, annualised **monthly** volatility, month-end drawdown. Theirs is gross
of costs and fees; ours are net of 20 bps each way.

| Book | CAGR | Vol | **Sharpe** | Sortino | Max DD | Calmar | Positive months |
|---|---|---|---|---|---|---|---|
| **Wright Momentum (published, gross)** | 31.2% | 20.0% | **1.31** | 2.28 | −21.7% | 1.43 | 66% |
| **MM stack, Nifty 250 (net)** | 33.9% | 19.8% | **1.46** | 2.48 | −26.5% | 1.28 | 69% |
| OM25 current pick, Nifty 250 (net) | 34.5% | 24.2% | 1.22 | 1.88 | −27.7% | 1.25 | 66% |
| L6 v2 rules, Nifty 250 (net) | 24.2% | 21.9% | 0.88 | 1.38 | −22.0% | 1.10 | 69% |
| L6 v2 rules, NSE 500 (net) | 25.2% | 25.0% | 0.81 | 1.23 | −32.0% | 0.79 | 68% |
| MidSmall 400 (synthetic) | 23.6% | 18.1% | 1.03 | 1.62 | −22.0% | 1.07 | 63% |
| Nifty 500 | 16.8% | 14.9% | 0.79 | 1.29 | −18.0% | 0.94 | 65% |

**Wright's Sharpe on this window is 1.31.** The MM stack beats it on Sharpe
(1.46), Sortino and CAGR while being net rather than gross — and loses on
drawdown, −26.5% against −21.7%, which is where their edge has always been.
Note the convention: on daily volatility the MM stack's Sharpe over the same
window is 1.50, not 1.46. Wright publish no Sharpe for this window; 1.31 is
computed here, not quoted.

### The last three years (2023-01-01 → 2026-09-09)

| Book | CAGR | Vol | Sharpe | Max DD | Calmar | Total |
|---|---|---|---|---|---|---|
| **MM stack, Nifty 250** | **27.3%** | 18.9% | **1.18** | −26.5% | 1.03 | 143% |
| OM25 current pick, Nifty 250 | 25.7% | 23.1% | 0.90 | −28.1% | 0.91 | 132% |
| MidSmall 400 (synthetic) | 18.8% | 16.0% | 0.86 | −22.8% | 0.83 | 89% |
| L6 v2 rules, Nifty 250 | 14.3% | 19.3% | 0.48 | −23.5% | 0.61 | 64% |
| L6 v2 rules, NSE 500 *(production)* | 13.7% | 20.7% | 0.42 | −35.3% | 0.39 | 61% |
| Nifty 500 | 11.2% | 13.5% | 0.46 | −18.8% | 0.59 | 48% |

**The new book is well ahead of both old ones, and the production book is the
worst of the set.** L6 v2 on its own production universe has returned 13.7% a
year over three years on honest data — behind the MidSmall 400 (18.8%) at
nearly twice its drawdown. That is a live-product finding, not a research one.

### Why medium-term trades lose money

MM stack, all 896 closed trades 2010-26:

| Holding period | Share | Avg P&L | Median | Win rate | Stop share | Total P&L contribution |
|---|---|---|---|---|---|---|
| 0-30 days | 10.7% | **−3.3%** | −3.2% | 37% | 9% | −316 |
| 31-60 days | 16.5% | **−1.6%** | −2.9% | 39% | 11% | −236 |
| 61-120 days | 29.1% | **−2.0%** | −4.5% | 40% | 23% | −530 |
| 121-250 days | 29.0% | +10.0% | +4.6% | 59% | 31% | +2,592 |
| 251+ days | 14.6% | **+60.4%** | +40.7% | **95%** | 32% | +7,915 |

The founder's observation is right but understates it: **every bucket under
four months is negative, and they are 56% of all trades.** The book earns
everything from the 44% that survive past 120 days, and almost all of it from
the 15% that pass a year.

Splitting each bucket by exit reason first suggested the stop was the cause —
in 61-120 days rank exits average **+1.0%** (n=202) while stop exits average
**−12.5%** (n=59). §13A tests that directly and finds it is not the cause.

## §13 — the stop, and multi-cap slots (10 trials) — post-OOS

### A. Stop level, including off

| Stop | IS | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Last 3y | Up / down | Mid-hold avg | Trades/yr |
|---|---|---|---|---|---|---|---|
| **off** | 1.12 | 24.5% / 1.11 / −27% | 0.43 / 1.72 / 1.24 | **28.2% / 1.24** | 1.07 / **0.65** | −1.6% | **100** |
| 15% | 1.11 | 24.4% / 1.11 / −27% | 0.67 / 1.80 / 1.00 | 24.2% / 1.00 | 1.10 / 0.85 | −1.4% | 136 |
| **20% (adopted)** | 1.10 | **25.7% / 1.18 / −26%** | 0.71 / 1.73 / 1.18 | 27.3% / 1.18 | 1.09 / 0.73 | −1.9% | 118 |
| 25% | 1.12 | 24.8% / 1.13 / −26% | 0.61 / 1.65 / 1.19 | 27.4% / 1.19 | 1.09 / 0.73 | −1.4% | 110 |
| 30% | 1.16 | 24.2% / 1.09 / −26% | 0.52 / 1.63 / 1.18 | 27.2% / 1.18 | 1.06 / 0.72 | −2.0% | 105 |

Two findings, and the second is the important one.

1. **The stop is a flat plateau, 1.09 to 1.18, and 20% is its top.** Removing
   the stop entirely costs 0.07 of Sharpe, *improves* the last three years
   (28.2% / 1.24 against 27.3% / 1.18), gives the best down-capture in the
   table (0.65) and cuts turnover from 118 to 100 trades a year. Its cost is
   2016-19, which falls from 0.71 to 0.43 — the stop is buying one sub-window.
2. **The stop is not what makes medium-term trades lose.** With no stop at all
   the 31-120 day buckets still average −1.6%, against −1.9% with the 20%
   stop. Removing the stop does not move those positions into profit; it moves
   them into later buckets or later rank exits at similar P&L.

So the medium-term loss is structural to momentum on this universe, not a
device artefact. A rule that cut it would have to act on state observable at
60-90 days, and every eventual 251+ winner (95% win rate, +60% average) passes
through that window first. That is the constraint any fix has to clear.

### B. Multi-cap slots — reserve K of 25 for the 251-500 band

Implemented as a slot quota, not a universe change: the panel is the NSE 500
with a point-in-time Nifty 250 core mask; each rebalance takes the top
(25 − K) core names and the top K names from outside the core, with the exit
buffer split between the two sleeves in proportion. Satellites sit at the
bottom of the top-25 block, so a bear truncation cuts them first.

| Cell | IS | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Last 3y | Up / down | Mid-hold avg |
|---|---|---|---|---|---|---|
| **Nifty 250 only (adopted)** | 1.10 | **25.7% / 1.18 / −26%** | 0.71 / 1.73 / 1.18 | **27.3% / 1.18** | 1.09 / **0.73** | −1.9% |
| NSE 500 panel, no quota | 1.06 | 22.3% / 0.91 / −36% | 0.49 / 1.68 / 0.72 | 19.9% / 0.72 | 1.10 / 1.19 | −1.5% |
| 22 core + 3 satellite | 0.97 | 21.5% / 0.96 / −27% | 0.44 / 1.49 / 1.01 | 23.1% / 1.01 | 1.04 / 0.83 | −3.5% |
| 20 core + 5 satellite | 0.92 | 20.5% / 0.89 / −30% | 0.40 / 1.47 / 0.86 | 20.4% / 0.86 | 1.01 / 0.87 | −3.3% |
| 17 core + 8 satellite | 0.99 | 20.4% / 0.89 / −32% | 0.39 / 1.45 / 0.89 | 20.9% / 0.89 | 1.02 / 0.86 | −3.0% |

**The idea does not work in this form, and the response is monotone: more
satellite is worse on every measure.** Against the adopted book, three
satellite slots cost 4.2pp of CAGR, 0.22 of Sharpe and 4.2pp of last-three-year
return; eight cost 5.3pp and 0.29.

The premise does not hold either. **Up-capture falls when satellites are added
(1.09 → 1.04 / 1.01 / 1.02), and down-capture worsens (0.73 → 0.83-0.87).**
§7 already showed NSE 500 and Nifty 250 have the *same* up-capture, 1.09 both;
NSE 500's problem was never upside, it was down-capture at 1.37. Momentum
selected from the 251-500 band is not the same thing as that band's upside.

One thing the quota does achieve: it is a better way to hold NSE 500 exposure
than simply running the NSE 500 book — at K=3 the drawdown improves from −36%
to −27% and the last three years from 19.9% to 23.1%. If a multi-cap product
is wanted for its own sake, the quota is the right mechanism. It is not an
alpha improvement over the Nifty 250 book.

Not adopted. Trial count post-OOS §8-§13: 170 cells.

## §14 — the mid-small universe as a book (5 trials) — post-OOS

**Answering a founder question, 2026-09-10: no strategy had ever been run on
a mid-small universe.** The MidSmall 400 has appeared in this repo only as a
*benchmark* (om25_rebuild §4f). The harness carries membership for four
universes only — Nifty 50 / 100 / LargeMidcap 250 / NSE 500
(`data/master/membership/`) — and `tasks/index_reconstruction` rebuilt those
four and deliberately not Midcap 150 or Smallcap 250. MM §1's universe grid
was Nifty 250 × NSE 500; §9's universe hypotheses (top-300, turnover floors)
all *narrowed* the panel. Nothing has gone the other way.

Universe here is the point-in-time complement: **NSE 500 members not in the
Nifty 250** at each signal date. That is exactly the construction §4f used for
the synthetic index before 2019, where it tracked the real Smallcap 250 at
0.986 daily correlation. It is a proxy for NIFTY MIDSMALLCAP 400, not the
index itself — the real Midcap 150 / Smallcap 250 membership does not exist in
the store. Capture is measured against the MidSmall 400, which is this book's
benchmark rather than the Nifty 250.

| Cell | IS | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Last 3y | Up / down vs MS400 | Trades/yr |
|---|---|---|---|---|---|---|
| Nifty 250 (adopted stack) *[control]* | 1.10 | **25.7% / 1.18 / −26%** | **0.71** / 1.73 / 1.18 | 27.3% / 1.18 / −26% | 1.09 / **0.73** | 118 |
| NSE 500 whole panel *[control]* | 1.06 | 22.3% / 0.91 / −36% | 0.49 / 1.68 / 0.72 | 19.9% / 0.72 / −36% | 1.10 / 1.19 | 144 |
| **Mid-small, 12m lookback** | **1.18** | 24.8% / 0.99 / **−35%** | **0.27** / 1.73 / 1.04 | 25.8% / 1.04 / −30% | **1.16** / 1.06 | 137 |
| Mid-small, 6m lookback | **1.49** | 19.5% / 0.73 / −30% | 0.34 / 1.37 / 0.59 | 16.2% / 0.59 / −24% | 0.80 / 0.86 | 174 |
| Mid-small, 12m, no bear rule, no stop | 1.03 | 21.6% / 0.80 / −43% | 0.34 / 1.25 / 0.85 | 22.3% / 0.85 / −30% | 1.10 / 1.16 | 96 |
| *Benchmark: MidSmall 400* | — | *14.9% / 0.55 / −51%* | — | *18.5%* | — | — |
| *Benchmark: Nifty 500* | — | *12.1% / 0.44 / −38%* | — | *11.2%* | — | — |

**Verdict: the upside premise is real and the book still does not clear the
Nifty 250 one.** Three readings:

1. **Mid-small has the highest up-capture we have measured — 1.16**, against
   1.09 for the Nifty 250 book and 1.10 for the whole NSE 500. This is the
   first evidence in the task that supports the founder's instinct about
   upside outside the large-mid band. §13B appeared to refute it, but that
   test *diluted* a core book with satellites, which removed core names; a
   pure mid-small book is a different question and answers differently.
2. **It gives the upside back on the downside and in 2016-19.** Down-capture
   1.06 against the core book's 0.73, drawdown −35% against −26%, and 2016-19
   at **0.27** — a clear G3 failure, worse than any Nifty 250 cell in the
   task. Net of that, OOS Sharpe is 0.99 against 1.18.
3. **Alpha over its own benchmark is slightly lower, not higher.** The
   mid-small book beats the MidSmall 400 by 9.9pp a year (24.8% vs 14.9%);
   the core book beats the Nifty 250 by 11.7pp (25.7% vs 14.0%). So it is not
   a bigger cushion — it is a similar cushion carried at more risk.

Two secondary findings:

- **The 6m lookback is the clearest overfit in the task.** It posts the best
  in-sample Sharpe of anything run (1.49) and the second-worst out-of-sample
  (0.73), with up-capture collapsing to 0.80. §1 preferred 6m on NSE 500; on
  the mid-small band that preference does not survive contact with 2016-26.
- **The risk devices matter more here than on the core.** Removing the bear
  rule and the stop takes the drawdown from −35% to −43% and the medium-hold
  average from −1.7% to −4.7%, a much larger swing than the same removal
  causes on the Nifty 250 book (§13A).

Not adopted. The open thread, not claimed: the bear rule, sector cap and stop
were all tuned on the Nifty 250 book. A down-capture device fitted to the
mid-small band is the one untried route to the "bigger cushion" — this book
has the raw upside and no risk control fitted to it. That would be a fresh
in-sample exercise on a held-back window, not another post-OOS cell.

Trial count post-OOS §8-§14: 175 cells.

## §15 — rebalance day of month (11 trials) — post-OOS

Founder 2026-09-10: the 1st may be sub-optimal; test days closer to the
15th-25th. `rebalance_day` added to both harnesses: the monthly signal is
the first trading day on or after that calendar day (day 1 reproduces the
engine's monthly dates exactly), execution the next session; the stop is
checked on the same day (§10's one-action-day rhythm). Numbered §15 because §11-§14 were added in a parallel session (G5 walk-forward, Wright's Sharpe, stop level and satellite slots, the mid-small book).

**MM stack, Nifty 250**
| Signal on first trading day ≥ | IS 2010-15 | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Wright window | 2010-26 |
|---|---|---|---|---|---|
| 1 | 20.0% / 1.10 | 25.7% / 1.18 / -26% | 0.71 / 1.73 / 1.18 | 33.9% / 1.50 | 23.6% / 1.15 |
| 5 | 18.3% / 0.97 | 21.9% / 0.97 / -28% | 0.25 / 1.77 / 0.98 | 31.0% / 1.34 | 20.6% / 0.96 |
| 10 | 16.6% / 0.89 | 21.5% / 0.92 / -33% | 0.41 / 1.51 / 0.91 | 27.6% / 1.15 | 19.7% / 0.90 |
| 15 | 16.9% / 0.89 | 22.8% / 1.01 / -33% | 0.42 / 1.52 / 1.12 | 31.8% / 1.43 | 20.7% / 0.97 |
| 20 | 17.3% / 0.91 | 23.4% / 1.07 / -31% | 0.47 / 1.61 / 1.16 | 31.9% / 1.48 | 21.2% / 1.01 |
| 25 | 17.4% / 0.94 | 21.5% / 0.96 / -31% | 0.56 / 1.24 / 1.08 | 27.4% / 1.20 | 20.0% / 0.95 |

**OM25 current pick, Nifty 250** (monthly stop check; with the weekly
check this configuration is 0.82 — §10)
| Signal on first trading day ≥ | IS 2010-15 | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Wright window | 2010-26 |
|---|---|---|---|---|---|
| 1 | 12.4% / 0.38 | 20.8% / 0.69 / -46% | 0.31 / 0.95 / 0.84 | 32.5% / 1.17 | 17.8% / 0.59 |
| 5 | 13.4% / 0.43 | 19.8% / 0.65 / -45% | 0.29 / 0.89 / 0.77 | 31.5% / 1.12 | 17.6% / 0.58 |
| 10 | 13.1% / 0.42 | 21.4% / 0.72 / -45% | 0.27 / 1.06 / 0.87 | 32.6% / 1.17 | 18.4% / 0.62 |
| 15 | 12.8% / 0.40 | 18.9% / 0.62 / -44% | 0.19 / 1.00 / 0.69 | 29.2% / 1.04 | 16.7% / 0.55 |
| 20 | 12.8% / 0.40 | 19.8% / 0.66 / -49% | 0.11 / 0.96 / 0.91 | 33.1% / 1.20 | 17.3% / 0.57 |
| 25 | 15.8% / 0.55 | 18.3% / 0.58 / -48% | 0.16 / 0.88 / 0.71 | 29.7% / 1.05 | 17.4% / 0.57 |

Read: for MM the first trading day is the best day in every window,
including the 2010-2015 window where nothing was tuned for it (1.10
against 0.89-0.97), and the best of the later days (the 20th, 1.07)
is 0.11 behind out of sample. The one caveat is that the stack's other
elements were all searched with day-1 rebalancing, so day 1 has had
130 cells of implicit selection; the in-sample gap says the preference
is real, the size of it is probably flattered. For OM25 the day effect
is noise (0.58-0.72, no ordering), and the monthly stop check costs it
0.1 of Sharpe and 10pp of drawdown against the weekly check (§10) — OM25
keeps the weekly stop review. **Day 1 stays for both books.**
