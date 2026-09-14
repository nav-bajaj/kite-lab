# §2 — head-to-head, 2026-09-11

All five arms through §22's adopted cell verbatim — buffer 20, stop 0.2,
inverse-vol capped 10%, bear 15, sector cap 5, monthly, Nifty 250 PIT, 20 bps
each way — with only `kind` swapped. Static 2016-01-01 to 2026-09-09.

Run: `python tasks/residual_momentum/lib/phase2.py`

**Control check: the MM arm reproduces its registry number exactly, 25.2% /
1.15 / −27%.** The comparison is valid.

| Arm | CAGR | Sharpe | maxDD | Vol | Skew | Kurt | Turnover | 16-19 | 20-22 | 23-26 |
|---|---|---|---|---|---|---|---|---|---|---|
| M12 | 22.8% | 0.91 | −34% | 19.5% | −0.91 | 10.8 | 2.43x | 0.41 | 1.33 | 1.05 |
| **MM** | **25.2%** | **1.15** | **−27%** | 17.6% | −0.84 | 9.6 | 2.39x | 0.69 | 1.73 | 1.10 |
| RM-12 | 22.1% | 1.00 | −31% | 17.1% | −0.92 | 9.8 | **2.00x** | 0.60 | 1.43 | 1.01 |
| RM-24 | 17.3% | 0.77 | −30% | **16.0%** | **−0.42** | **5.6** | 3.95x | 0.27 | 1.42 | 0.75 |
| RM-36 | 16.9% | 0.72 | −32% | 16.5% | −0.76 | 8.7 | 3.19x | 0.35 | 1.12 | 0.76 |

## Verdict: no. Residual momentum loses on our stack.

The bar was **> +0.10 Sharpe** over the locked rules. RM-12, the best
residual arm, comes in at **−0.15**. RM-24 and RM-36 are −0.38 and −0.43.
Nothing is close, and the shortfall is not a regime artifact: MM wins every
sub-window against every arm.

Nor is the drawdown motivation delivered. The whole reason this was worth a
pass is that MM's weak point is the tail, and **no residual arm improves on
MM's −27%** — RM-12 is −31%, RM-24 −30%, RM-36 −32%.

## What the paper's mechanism did and did not do here

The vol reduction is **real but far too small to matter**. Every residual arm
runs below MM's 17.6% (RM-12 17.1%, RM-24 16.0%) and well below plain M12's
19.5%. The direction is the paper's; the magnitude is not. Blitz et al. cut
volatility from 22.7% to 12.5% — nearly in half. We get 17.6% to 17.1%.

The **tail improvement shows up only in the paper-faithful arms**. RM-24
produces genuinely better distribution shape than MM — skew −0.42 against
−0.84, kurtosis 5.6 against 9.6. That is the paper's crash result reproducing
on Indian large/mid caps, and it is the one claim that clearly survives.

But it comes with the split that kills the whole idea: **the construction
that fixes the tail is the one that costs the most return, and the
construction that preserves return does not fix the tail.** RM-24 buys its
skew with 7.9 points of CAGR. RM-12 keeps within 3.1 points of MM's CAGR and
delivers skew of −0.92, no better than MM's −0.84. There is no arm that gets
both, and no reason visible in these numbers to expect one exists.

## Three things worth keeping regardless

**1. RM-12 cuts turnover by 16%** — 2.00x against MM's 2.39x, and the
advantage holds at every skip tested (1.93-2.00x against 2.39-2.54x). This
directly contradicts the §1 worry that a regression residual would be a
noisier month-to-month ranking. It is the paper-faithful arms that are noisy:
RM-24 turns over 3.95x, RM-36 3.19x, both far above anything in the standing
book. If turnover ever becomes the binding constraint, the alpha construction
is a known lever.

**2. MM's vol-adjustment earns its place, and not where §1 suggested.** MM
beats M12 by 0.24 Sharpe (1.15 vs 0.91) and 7 points of drawdown (−27% vs
−34%) — yet §1 measured the two rankings at 0.979 rank correlation. The
reconciliation is that the book takes 25 names from 250: a reordering too
small to move a universe-wide correlation can still substantially change
which names reach the top of a concentrated book. Worth remembering the next
time a rank correlation is used to argue two scores are interchangeable.

**3. The §1 skip-month flag was a false alarm, and the test says so.** §1
pre-registered that RM-12's +0.259 tell — a tilt toward names that rose in
the *skipped* month, six times MM's +0.04 — might be an adverse short-term
reversal exposure, with skip=42 as the sensitivity. It is not:

| Arm | skip 21 | skip 42 | skip 63 |
|---|---|---|---|
| MM | **1.15** | 0.93 | 0.97 |
| RM-12 | 1.00 | 1.01 | 0.93 |

RM-12 is flat from 21 to 42 (1.00 → 1.01). The tell was measuring something
real about the score but it was not costing anything.

Note the trap in that table: at skip=42 RM-12 (1.01) *beats* MM (0.93). That
is not a finding, it is a worse configuration for both, and picking skip=42
to manufacture a win for RM-12 is exactly the parameter-mining the gates
exist to stop. MM at its locked skip=21 beats every cell in the table.

## What this does not settle

The factor set is market + sector, not Fama-French — no book-to-market,
per PLAN.md. In the paper's large-cap table HML carries the largest single
term (HML_UP 1.31), and the PLAN's working hypothesis was that sector
residualisation would pick up much of what HML does in India. **These results
cannot distinguish "residual momentum does not work here" from "residual
momentum needs a value factor we cannot build."** That remains the honest
limit of this pass, and it is a reason to source fundamentals, not a reason
to re-run this without them.

Two smaller caveats stand from §1: sector labels are not point-in-time
(inherited from the map the sector cap already uses), and returns are not
winsorised, so single extreme sessions lean on the fits.

## Recommendation

Close it. No change to `tasks/mm_rebuild/MECHANICS.md`. §3 does not run —
it was gated on §2 clearing, and it did not clear.

The standing books survive a serious challenge from a well-cited result,
which is worth more than a marginal win would have been. If fundamentals are
ever sourced for the PEAD thread, a proper FF3 residual is cheap to retry
from `lib/residual.py` — the harness is built and the controls reproduce.
