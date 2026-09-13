# Results — exit_asymmetry_2026

**Verdict: no exit family wins. The asymmetry is real and it is not a leak —
it is the price of the right tail.** X0 reproduces exactly (476 calls / 41.6%
/ +13.60% on 2021+ closed-only), so the tape is the one PLAN.md measured. Nine
cells beat X0 on full-span expectancy and every one of them is a **hold-time
artifact**: they are all un-backstopped rules that cannot exit until they arm,
so they run mean holds of 330-559 sessions against X0's 103 and leave 11-18%
of calls never closed. Per unit of time they are far worse — the nominal
winner X1 (A=25, k=50, no backstop) returns **19% a year per call against
X0's 42%**, and its per-call alpha is **+5.24% against X0's +10.29%**. Its E5
pass is a survivorship illusion: on 2021+ it leaves 183 of 521 calls open, and
those 183 are exactly the ones X0 closed at +1.41%, which is how a 41.6% win
rate becomes 99.7%. Among the like-for-like cells — anything with a bounded
hold — **not one beats X0 on expectancy**; the best is +13.33% against
+15.51%. The families do deliver what they were designed to deliver: share of
peak gain kept rises from X0's **24.1%** to **41.7%** (X1 A=25 k=50 + ma150)
and **54.3%** (X1 A=25 k=65 + ma150), and it costs 3.2pp and 6.7pp of
expectancy respectively. E6 is arithmetically cleared by the nominal winner
(+47.58% against a Gumbel bound of +34.13%) but **the test is void** — the
statistic being maximised is not comparable across cells when hold time varies
5×. PLAN's upper bound of +19.4% assumed the floor fills exactly; with the
task's actual fill (OHLC/4 of the session after the close breaches the floor,
−0.2%) the same rule delivers +10.89% on 2021+ closed-only, i.e. **−2.7pp, not
+5.8pp**. The give-back is the fill, and it is not recoverable without
intraday data, which is out of scope.

## Step 1 — X0 confirmation

| | PLAN target | Measured |
|---|---|---|
| 2021+ closed-only calls | ~476 | **476** |
| win | ~41% | **41.6%** |
| expectancy | +13.6% | **+13.60%** |
| Full-span tape | 1,828 | **1,828** |
| Full-span median share of peak kept | ~20% | 24.1% |

Tape is `trigger_calls_2026/data/tapes.parquet`, `kind=="T3"`, `rk<=20`,
de-duplicated to one open position per name. Confirmed; the grid ran.

## Step 2 — the grid, all 39 cells

Sorted by full-span expectancy. `ann/call` is the per-call return annualised
by its own mean hold — the column PLAN.md's "flag, don't celebrate" rule
requires and the one the expectancy column hides. `open` is the share of calls
the rule never closes. `keep` is the median share of peak gain kept on calls
that reached +10%. E1-E5 as pre-registered; E6 is a single grid-level test,
reported below.

| Family | Params | Backstop | n | win | avg win | avg loss | **exp** | alpha | ann/call | med hold | mean hold | open | keep | 2021+ n | 2021+ exp | E1 | E2 | E3 | E4 | E5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 | A=25 k=50 | — | 1,828 | 87.2% | +62.4% | -53.5% | **+47.58%** | +5.24% | 19% | 250 | 559 | 18.0% | 46.1% | 338 | +35.3% | Y | Y | Y | Y | Y |
| X2 | A=25 m=5 | — | 1,828 | 79.3% | +55.3% | -36.1% | **+36.37%** | -1.84% | 16% | 240 | 512 | 16.8% | 46.1% | 344 | +42.52% | Y | Y | Y | Y | Y |
| X1 | A=25 k=65 | — | 1,828 | 87.4% | +42.9% | -54.0% | **+30.67%** | -5.10% | 15% | 184 | 476 | 15.9% | 60.0% | 359 | +34.99% | Y | Y | · | Y | Y |
| X1 | A=15 k=50 | — | 1,828 | 89.4% | +38.3% | -48.1% | **+29.16%** | -0.22% | 18% | 127 | 386 | 12.4% | 44.9% | 401 | +23.69% | Y | Y | · | Y | Y |
| X2 | A=15 m=5 | — | 1,828 | 70.6% | +50.8% | -23.4% | **+29.01%** | +0.36% | 18% | 169 | 389 | 12.6% | 35.9% | 389 | +31.79% | Y | Y | Y | Y | Y |
| X2 | A=25 m=3 | — | 1,828 | 85.5% | +41.4% | -47.8% | **+28.51%** | -6.56% | 14% | 183 | 469 | 15.6% | 56.2% | 359 | +36.46% | Y | Y | · | Y | Y |
| X8 | A=25 k=60/75 | — | 1,828 | 87.5% | +39.9% | -54.5% | **+28.1%** | -7.16% | 14% | 178 | 464 | 15.8% | 60.3% | 359 | +35.02% | Y | Y | · | Y | Y |
| X2 | A=15 m=3 | — | 1,828 | 81.9% | +32.3% | -30.7% | **+20.97%** | -4.86% | 15% | 115 | 343 | 11.4% | 47.3% | 406 | +25.92% | Y | Y | · | Y | Y |
| X1 | A=15 k=65 | — | 1,828 | 90.6% | +27.1% | -53.9% | **+19.5%** | -6.00% | 15% | 90 | 330 | 11.1% | 58.6% | 414 | +23.44% | Y | Y | · | Y | Y |
| **X0** | — | — | 1,828 | 41.2% | +59.1% | -15.1% | **+15.51%** | +10.29% | 42% | 83 | 103 | 3.0% | 24.1% | 476 | +13.6% | · | · | Y | Y | · |
| X4 | Y=5 N=63 | ma150 | 1,828 | 46.1% | +45.5% | -14.2% | **+13.33%** | +8.78% | 44% | 64 | 86 | 2.7% | 24.1% | 481 | +9.95% | · | · | · | · | · |
| X4 | Y=5 N=63 | — | 1,828 | 46.1% | +45.5% | -14.2% | **+13.33%** | +8.78% | 44% | 64 | 86 | 2.7% | 24.1% | 481 | +9.95% | · | · | · | · | · |
| X4 | Y=10 N=63 | — | 1,828 | 47.9% | +42.4% | -14.6% | **+12.73%** | +8.34% | 45% | 64 | 81 | 2.6% | 30.6% | 482 | +8.6% | · | · | · | Y | · |
| X4 | Y=10 N=63 | ma150 | 1,828 | 47.9% | +42.4% | -14.6% | **+12.73%** | +8.34% | 45% | 64 | 81 | 2.6% | 30.6% | 482 | +8.6% | · | · | · | Y | · |
| X2 | A=25 m=5 | ma150 | 1,828 | 43.2% | +48.9% | -15.0% | **+12.62%** | +8.28% | 41% | 74 | 88 | 2.5% | 29.3% | 485 | +12.26% | · | · | · | Y | · |
| X1 | A=25 k=50 | ma150 | 1,828 | 47.1% | +43.6% | -15.5% | **+12.33%** | +8.27% | 43% | 64 | 82 | 2.4% | 41.7% | 488 | +10.89% | · | Y | · | Y | · |
| X2 | A=15 m=5 | ma150 | 1,828 | 43.2% | +47.4% | -14.5% | **+12.25%** | +8.10% | 41% | 70 | 85 | 2.4% | 27.6% | 485 | +12.01% | · | · | · | · | · |
| X4 | Y=5 N=42 | — | 1,828 | 47.8% | +38.7% | -12.7% | **+11.83%** | +8.00% | 49% | 43 | 71 | 2.2% | 23.9% | 490 | +7.28% | · | · | · | Y | · |
| X4 | Y=5 N=42 | ma150 | 1,828 | 47.8% | +38.7% | -12.7% | **+11.83%** | +8.00% | 49% | 43 | 71 | 2.2% | 23.9% | 490 | +7.28% | · | · | · | Y | · |
| X6 | R=100 | — | 1,828 | 37.0% | +44.1% | -8.7% | **+10.83%** | +6.30% | 45% | 22 | 70 | 3.0% | 38.4% | 490 | +7.2% | · | Y | · | Y | · |
| X5 | — | — | 1,828 | 37.0% | +44.0% | -8.7% | **+10.82%** | +6.28% | 45% | 22 | 70 | 3.0% | 38.4% | 490 | +7.2% | · | Y | · | Y | · |
| X6 | R=50 | — | 1,828 | 37.4% | +42.9% | -8.7% | **+10.61%** | +6.20% | 45% | 21 | 69 | 3.0% | 39.3% | 490 | +7.14% | · | Y | · | Y | · |
| X4 | Y=10 N=42 | — | 1,828 | 49.9% | +34.0% | -13.1% | **+10.4%** | +6.97% | 49% | 43 | 63 | 1.8% | 32.6% | 495 | +5.23% | · | · | · | Y | · |
| X4 | Y=10 N=42 | ma150 | 1,828 | 49.9% | +34.0% | -13.1% | **+10.4%** | +6.97% | 49% | 43 | 63 | 1.8% | 32.6% | 495 | +5.23% | · | · | · | Y | · |
| X1 | A=15 k=50 | ma150 | 1,828 | 55.2% | +31.8% | -16.0% | **+10.35%** | +6.99% | 46% | 50 | 66 | 1.9% | 43.2% | 495 | +9.44% | · | Y | · | Y | · |
| X1 | A=25 k=65 | ma150 | 1,828 | 47.2% | +36.1% | -15.6% | **+8.8%** | +5.57% | 37% | 57 | 68 | 2.1% | 54.3% | 492 | +8.86% | · | Y | · | Y | · |
| X2 | A=25 m=3 | ma150 | 1,828 | 46.2% | +36.2% | -15.4% | **+8.46%** | +5.25% | 34% | 63 | 70 | 2.1% | 44.6% | 491 | +9.38% | · | Y | · | Y | · |
| X3 | N=63 | — | 1,828 | 46.9% | +33.7% | -14.6% | **+8.11%** | +5.05% | 37% | 64 | 63 | 1.9% | 43.3% | 493 | +7.97% | · | Y | · | Y | · |
| X3 | N=63 | ma150 | 1,828 | 46.9% | +33.7% | -14.6% | **+8.11%** | +5.05% | 37% | 64 | 63 | 1.9% | 43.3% | 493 | +7.97% | · | Y | · | Y | · |
| X7 | N=42 Y=5 / A=25 k=60 | — | 1,828 | 54.2% | +26.9% | -14.5% | **+7.94%** | +4.61% | 37% | 43 | 61 | 1.7% | 45.8% | 501 | +6.07% | · | Y | · | Y | · |
| X8 | A=25 k=60/75 | ma150 | 1,828 | 47.2% | +33.7% | -15.6% | **+7.72%** | +4.59% | 33% | 57 | 66 | 2.1% | 54.2% | 492 | +8.37% | · | Y | · | Y | · |
| X2 | A=15 m=3 | ma150 | 1,828 | 50.0% | +30.1% | -15.0% | **+7.57%** | +4.69% | 35% | 54 | 62 | 1.9% | 40.3% | 494 | +8.76% | · | Y | · | Y | · |
| X3 | N=42 | ma150 | 1,828 | 46.4% | +30.0% | -12.7% | **+7.14%** | +4.68% | 41% | 43 | 51 | 1.4% | 41.6% | 501 | +6.98% | · | Y | · | Y | · |
| X3 | N=42 | — | 1,828 | 46.4% | +30.0% | -12.7% | **+7.14%** | +4.68% | 41% | 43 | 51 | 1.4% | 41.6% | 501 | +6.98% | · | Y | · | Y | · |
| X7 | N=42 Y=5 / A=25 k=60 | ma150 | 1,828 | 50.9% | +26.5% | -13.1% | **+7.06%** | +4.57% | 41% | 43 | 50 | 1.6% | 45.6% | 501 | +5.4% | · | Y | · | Y | · |
| X1 | A=15 k=65 | ma150 | 1,828 | 56.1% | +24.9% | -16.3% | **+6.8%** | +4.22% | 38% | 41 | 52 | 1.6% | 56.3% | 499 | +7.13% | · | Y | · | Y | · |
| X5 | — | ma150 | 1,828 | 35.6% | +29.4% | -8.1% | **+5.26%** | +3.81% | 50% | 21 | 32 | 1.3% | 36.6% | 504 | +5.22% | · | Y | · | Y | · |
| X6 | R=100 | ma150 | 1,828 | 35.6% | +29.5% | -8.1% | **+5.26%** | +3.81% | 50% | 21 | 32 | 1.3% | 36.6% | 504 | +5.22% | · | Y | · | Y | · |
| X6 | R=50 | ma150 | 1,828 | 36.0% | +28.7% | -8.1% | **+5.11%** | +3.78% | 50% | 21 | 31 | 1.3% | 37.5% | 504 | +5.13% | · | Y | · | Y | · |

**Trial count.** The pre-registered parameter grid is X1 4 · X2 4 · X3 2 ·
X4 4 · X5 1 · X6 2 · X7 1 · X8 1 = 19 family cells, ×2 for the backstop
variant = 38, plus X0 = **39**. PLAN.md's arithmetic (`X0 + 8 + 4 + 2 + 4 + 1
+ 2 + 1 + 1 = 23`) does not add up and its X1 count of 8 does not match
A∈{15,25}×k∈{50,65}; the parameter grid itself is unambiguous and was run
exactly as written. No cells were added.

**X4's two rows are identical by construction** — X4 already contains ma150,
so the backstop variant is a no-op. Same for X3 (it is ma150 then ma50; the
backstop can only fire where the family already fires in the first phase).
Both are reported rather than silently collapsed.

## Per era — top 5 by expectancy

| Cell | 2006-12 | 2013-19 | 2020-26 | mean hold | never closed |
|---|---|---|---|---|---|
| X1 A=25 k=50, no backstop | +59.07% | +50.26% | +33.68% | 559 | 18.0% |
| X2 A=25 m=5, no backstop | +29.47% | +46.63% | +32.53% | 512 | 16.8% |
| X1 A=25 k=65, no backstop | +32.11% | +34.78% | +25.05% | 476 | 15.9% |
| X1 A=15 k=50, no backstop | +32.30% | +29.04% | +26.23% | 386 | 12.4% |
| X2 A=15 m=5, no backstop | +21.89% | +36.34% | +28.41% | 389 | 12.6% |
| *X0 reference* | *+9.31%* | *+13.71%* | *+23.36%* | *103* | *3.0%* |

All five pass E4 on the letter of the rule. All five have mean holds of 3.8× to
5.4× X0's, and the era pattern is the tell: their best era is **2006-12**,
the era with the most time left in the sample for an unclosed position to
recover. X0's expectancy rises monotonically across eras; the artifact cells
fall.

## Gumbel bound — E6

| | Value |
|---|---|
| Trials (excluding X0 from the draw pool) | 38 of 39 cells |
| Mean expectancy across cells | +14.39% |
| sd | 9.87pp |
| z for n=39 | 2.000 |
| **Gumbel E[max]** | **+34.13%** |
| Best cell (X1 A=25 k=50, no backstop) | **+47.58%** |
| Clears arithmetically? | Yes |
| **Counts?** | **No** |

The bound is computed on a statistic that is not comparable across the cells
it ranks. An sd of 9.87pp on a grid whose whole spread is driven by mean hold
ranging 31 to 559 sessions is not measuring exit quality. On the comparable
sub-grid — the 20 cells with a bounded hold — the spread is +5.11% to +13.33%
and **the maximum is below X0**, so there is nothing for a multiplicity bound
to adjudicate. E6 is recorded as void, not as passed.

## Step 4 — trade by trade, 2021-2026

`data/best_vs_x0_2021.csv`, all 521 calls entered 2021 or later, with X0's
outcome, the nominal grid winner's (X1 A=25 k=50, no backstop) and the same
parameters with the ma150 backstop, which is the like-for-like reading.

| Basis | closed | still open | win (closed) | exp (closed) | exp (all, open marked) | med hold |
|---|---|---|---|---|---|---|
| X0 | 476 | 45 | 41.6% | **+13.60%** | +17.40% | 82 |
| X1 A=25 k=50, no backstop | 338 | **183** | **99.7%** | +35.30% | +29.23% | 171 |
| X1 A=25 k=50, + ma150 | 488 | 33 | 48.4% | **+10.89%** | +13.86% | 63 |

**The 99.7% win rate is the whole artifact in one number.** The rule closes a
position only when a ratchet floor is breached, and a floor only exists once
the call has been up 25%, so a call that never works is never closed. The 183
open calls are the losers: X0 closed those same 183 names at **+1.41%**
average, and the un-backstopped rule carries them at a **+18.0%** unrealised
mark. Remove the open positions from the denominator and only winners remain.

Backstopped, on the same 521 calls and the same parameters, the rule beats X0
on **20.3%** of calls. It raises win rate 41.6% → 48.4% and median share of
peak kept 24.1% → 41.7%, and it loses 2.7pp of expectancy doing it. That is
the real trade the founder is being offered: **a calmer tape that pays less**.

## What the eight families actually showed

| Family | The idea | What happened |
|---|---|---|
| X1 profit-lock ratchet | cap give-back as a share of earnings | works as designed — keep rises to 41.7-56.3% — and costs 3.2-8.7pp of expectancy at every parameter |
| X2 armed chandelier | peak trail that exists only once earned | same shape, slightly worse; best backstopped cell +12.62% |
| X3 age-scaled trail | the two-phase instinct, simplest form | −7.4pp. Switching to ma50 at day 42/63 cuts the mature winner, which is the one cohort that was working |
| X4 thesis time-box | kill the pop-and-fade young call | the *only* family that improves win rate without wrecking hold (46-50% win, 63-86 mean hold) and still loses 2.2-5.1pp — the young calls it kills include the ones that later ran |
| X5 state exit | the screen's own "thesis over" | −4.7pp, median hold 22. Leaving LEADING/EXTENDED is far too fast a trigger |
| X6 rank exit | rank was the reason to call | indistinguishable from X5 (−4.7 to −4.9pp); rank and state fire together |
| X7 two-phase composite | the founder's proposal as one rule | −7.6pp. Both halves are individually negative; combining them does not help |
| X8 regime-tightened X1 | market label sets tolerance | identical to X1 A=25 k=65 to within 0.4pp — tightening k to 75 on deteriorating breadth changes almost nothing |

X4 is the only family worth a second look, and only because of *where* it
fails: it improves the win rate by 5-9pp and shortens hold by 20-40% while
losing 2.2pp of expectancy. Everything else in the grid loses more.

## Blocked

- Nothing failed to run. All 39 cells completed on all 1,828 calls.
- **E6 is void, not passed** — see the Gumbel section. The pre-registered gate
  battery has no hold-time control, so a rule that refuses to close losers
  passes E1-E5 mechanically. That is a gate design flaw, recorded here rather
  than patched mid-task: no cell was removed and no gate was changed.
- The `exit_asymmetry_2026` families are heterogeneous (a ratchet, a
  time-box, a non-price state rule) and are implemented in
  `lib/exitsim.py` inside this folder rather than as branches in
  `breakout_calls_2026/lib/exits.py`, whose `simulate` only models level
  trails. `exits.py` was not modified by this task.

## Follow-ups

1. **Re-gate with a hold control before any exit work continues.** The
   minimum fix is two lines: require `open share ≤ 5%` and `mean hold within
   ±25% of X0`. Under that, 20 of 39 cells survive and none beats X0 — which
   is the answer, delivered in one pass instead of thirty-nine.
2. The PLAN's +19.4% upper bound should be restated. It assumed an exact fill
   at the floor; the realisable version is +10.89% on the same basis, i.e.
   below X0. The 8.5pp difference is pure fill assumption and is the single
   largest number in this task.
3. X4 (thesis time-box) is the one family whose failure is informative:
   it costs 2.2pp to buy +9pp of win rate and a 40% shorter hold. If the
   product constraint is capital turnover or client experience rather than
   expectancy, X4 Y=10 N=42 is the cell to price — +10.40%, 49.9% win, 63
   mean hold, 32.6% of peak kept. It is a worse strategy and a different
   product; that is a founder call, not a research one.
4. The measured asymmetry stands and is unexplained by anything tested here:
   calls that peak inside two months close at a loss, calls that peak after
   three months keep half. Every exit rule in this grid acts on price or
   state *after* the peak. Nothing tested acts on the distinction PLAN.md
   actually found, which is **when** the peak arrives. A rule conditioned on
   peak age — not on peak depth — is the untested idea this task leaves open.
