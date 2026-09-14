# Results — residual momentum

**Status: closed, not adopted. No change to `tasks/mm_rebuild/MECHANICS.md`.**

Opened 2026-09-11, closed 2026-09-14. One pass, as scoped.

## What was asked and what was delivered

Test Blitz, Huij and Martens (2011) *Residual Momentum* — rank stocks on the
part of their return not explained by common factors — against the locked MM
book, at the standing quarterly-challenger bar of **> +0.10 Sharpe**.

Delivered in full: three residual constructions plus two baselines, all run
through §22's adopted cell verbatim with only `kind` swapped. §3
(interactions) did not run; it was gated on §2 clearing, and §2 failed.

## The answer

Static 2016-01-01 to 2026-09-09, Nifty 250 PIT, 20 bps each way:

| Arm | CAGR | Sharpe | maxDD | Vol | Skew | Kurt | Turnover |
|---|---|---|---|---|---|---|---|
| M12 (plain 12-1) | 22.8% | 0.91 | −34% | 19.5% | −0.91 | 10.8 | 2.43x |
| **MM (standing)** | **25.2%** | **1.15** | **−27%** | 17.6% | −0.84 | 9.6 | 2.39x |
| RM-12 | 22.1% | 1.00 | −31% | 17.1% | −0.92 | 9.8 | **2.00x** |
| RM-24 | 17.3% | 0.77 | −30% | 16.0% | **−0.42** | **5.6** | 3.95x |
| RM-36 | 16.9% | 0.72 | −32% | 16.5% | −0.76 | 8.7 | 3.19x |

Best residual arm is **−0.15 Sharpe** against a **+0.10** bar. MM wins every
sub-window. **No residual arm improves MM's −27% drawdown**, which was the
motivating case for the whole pass.

The MM arm reproduced its registry number exactly (25.2% / 1.15 / −27%), so
the comparison is a like-for-like test and not a harness artifact.

## Why it failed

The paper's mechanism is present but an order of magnitude too weak. Every
residual arm cuts volatility in the right direction, but Blitz et al. go
22.7% → 12.5% while we go 17.6% → 17.1%.

The crash result does reproduce, on RM-24: skew −0.42 against MM's −0.84,
kurtosis 5.6 against 9.6. But it comes with the split that ends the idea —
**the construction that fixes the tail costs the most return (RM-24 gives up
7.9 points of CAGR), and the construction that preserves return does not fix
the tail** (RM-12's −0.92 skew is no better than MM's −0.84). No arm gets
both.

## Findings worth keeping

1. **A 12-month estimation window cannot use the paper's construction.** OLS
   with an intercept pins residuals to sum to zero over the estimation
   sample, so fitting and summing over near-identical windows collapses the
   score into a one-month *reversal* signal. It fails silently. The fix —
   read the intercept instead of summing residuals — is in `lib/residual.py`
   as `mode="alpha"`. §1 confirmed the mechanism empirically and
   monotonically: contamination scales with the formation/estimation ratio
   (RM-24 at 50% is measurably contaminated, RM-36 at the paper's 33% much
   less, RM-12 not at all).

2. **RM-12 costs nothing in eligibility** — it scores 246.7 names per
   rebalance, identical to MM, against RM-24's 240.9 and RM-36's 234.3.

3. **RM-12 cuts turnover 16%** (2.00x vs 2.39x), holding at every skip
   tested. A known lever if trading costs ever bind. The paper-faithful arms
   go the other way (3.95x, 3.19x).

4. **MM's vol-adjustment earns its place.** It beats plain M12 by 0.24
   Sharpe and 7 points of drawdown despite the two rankings correlating
   0.979 — because the book takes 25 names from 250, and a reordering too
   small to move a universe-wide correlation still changes who reaches the
   top. Caution against using rank correlation to argue two scores are
   interchangeable.

5. **The 36-month history rule really does exclude the mid-cap growth names**
   (VBL, ADANIGREEN at median rank 1, ATGL, DMART, IRCTC, POLYCAB) — but the
   claim that excluding them costs return did **not** survive de-overlapping:
   +9.55 pp becomes +0.96 pp on ~10 independent windows, positive in 4 of 10,
   carried by one 2020-22 Adani episode.

## What this does not settle

The factor set is market + sector, not Fama-French — no book-to-market,
because that needs the fundamentals feed we do not have. In the paper's own
large-cap table HML carries the largest single term. **These results cannot
separate "residual momentum does not work here" from "residual momentum needs
a value factor we cannot build."** That is a reason to source fundamentals,
not a reason to re-run this without them — and it is the same feed the PEAD
thread (`tasks/donchian_channel/PRODUCT_HANDOFF.md`) has been waiting on.

Smaller caveats: sector labels are not point-in-time (inherited from the map
the sector cap already uses), and returns are not winsorised.

## Deferred

- §3a relaxed sector cap on a residual score, §3b regime gate off. Both were
  gated on §2 clearing.
- An FF3 retry if fundamentals are ever sourced. Cheap: `lib/residual.py`
  takes an extra factor column, the harness is built, and the controls
  reproduce.

## Verification log

| Check | Outcome |
|---|---|
| MM control vs registry | Reproduces exactly, 25.2% / 1.15 / −27% |
| RM-12 degeneracy tell | +0.259, no negative pinning — construction sound |
| Pre-registered skip sensitivity | False alarm; RM-12 flat 21 → 42 (1.00 → 1.01) |
| Sector factor contamination | Found and fixed before any result was produced — factors were being built over all 1,326 panel symbols, pulling in CHEMPLASTS at +3507% on 2021-08-24 |
| Accelerate BLAS matmul warnings | Cosmetic; 0 non-finite or exploded betas in 95k fits, `X @ beta` bit-identical to elementwise |

## Reproducing

```
python tasks/residual_momentum/lib/diag_eligibility.py    # §0
python tasks/residual_momentum/lib/diag_scores.py         # §1
python tasks/residual_momentum/lib/phase2.py              # §2
```

Report CSVs are not committed — `*.csv` is gitignored repo-wide and the
mm_rebuild convention commits run `config.json` only. Every number in
`report/*.md` regenerates from the three scripts above; the backtests
themselves are cached in `tasks/mm_rebuild/runs/<id>/`.
