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
