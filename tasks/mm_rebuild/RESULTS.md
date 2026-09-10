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
