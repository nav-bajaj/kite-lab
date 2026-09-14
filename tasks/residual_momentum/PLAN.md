# Residual momentum — does stripping the factor-explained return improve MM?

## Why

Blitz, Huij and Martens (2011), *Residual Momentum*, Journal of Empirical
Finance. Ranking stocks on residual returns rather than total returns
roughly doubles the Sharpe ratio of a momentum strategy — 0.45 to 0.90 on
the full CRSP sample, 0.36 to 0.60 restricted to large caps — almost
entirely by cutting volatility (22.7% to 12.5%), with return slightly
higher. The mechanism is Grundy-Martin: a total-return momentum book picks
up whatever the factors did during the formation window, so it is
implicitly long the factors that just ran and is hurt when they turn.

Three reasons this is worth one pass on our stack:

1. **No new data.** The market factor is in `data/master/benchmarks/`, the
   sector labels in `tasks/mm_rebuild/sector/sector_v2_lookup.csv` (with
   `as_of` dates, so point-in-time), and the per-name dailies in
   `data/master/panels/pr/`. Nothing needs sourcing. We cannot build a real
   HML — book-to-market needs the fundamentals feed we do not have — so the
   factor set here is market + sector, not Fama-French. See "What we are
   not testing".
2. **It is a score swap, nothing else.** Book mechanics, buffer, sizing,
   sector cap, regime gate, stop and the one-order-day rhythm all stay as
   locked in `tasks/mm_rebuild/MECHANICS.md`. That is exactly the shape of
   change the quarterly challenger protocol was written to adjudicate.
3. **It attacks the documented weak point.** MM's problem is not return, it
   is the tail: −27% static, −31% process band, gate at −40%. The paper's
   crash mechanism is the formation-period factor tilt flipping — which is
   what our Nifty 100 ROC31 regime gate is a bolt-on patch for. Residual
   momentum attacks it at the signal instead.

MM is already half of the construction. MM ranks `return / vol`; residual
momentum ranks `residual return / residual vol`. The standardisation is
done. The paper's footnote 2 reports the *non*-standardised residual
version at 0.89 Sharpe against 0.90 standardised, so the residualisation is
doing all the work and MM's existing vol-adjustment is not already
capturing it. The delta is live.

## The 12-month constraint, and why the paper's construction cannot deliver it

Founder call 2026-09-11: estimate over 12 months, not the paper's 36, because
a 36-month history requirement excludes the newly-listed mid-cap growth
names that Nifty 250 keeps admitting.

The paper's construction cannot do this. OLS with an intercept forces
residuals to sum to zero over the estimation sample. Fit betas over a
252-session window and then sum residuals over the 252-session window
ending 21 sessions earlier, and the score collapses to minus the residual
return of the most recent 21 sessions — a one-month reversal signal, which
is precisely what the skip-month exists to avoid. It would not fail loudly;
it would backtest as an inverted signal. The paper uses 36/11 because the
formation window is then only ~31% of the estimation window, so residuals
inside it are not pinned to zero. It is a ratio constraint, not a
preference for long histories.

So the 12-month version reads the **intercept** rather than summing
residuals:

```
r_i,d = alpha_i + b_m * MKT_d + b_s * SECTOR_d + e_i,d
        over the 252 sessions ending 21 sessions before the signal date
score = alpha_i / sd(e_i)
```

No degeneracy — alpha is read, not summed to zero. ~231 daily observations
per fit, so the betas are far better conditioned than the paper's 36 monthly
points. History requirement is the same 252+21 window MM already needs, so
RM-12 adds **no** eligibility cost over the standing book.

The paper excludes alpha from its score, but for a reason that dissolves
here: their alpha is fit over 36 months, two-thirds of it outside the
formation window, so it contaminates the score with long-term reversal. When
the estimation window *is* the formation window, alpha is exactly the
stock-specific return over that window.

## Candidates

| | Construction | Estimation window | History needed |
|---|---|---|---|
| MM | `return / vol` over 252/21 | — | 273 sessions |
| RM-12 | `alpha / sd(resid)`, daily, over 252/21 | = formation window | 273 sessions |
| RM-24 | cumulative residual / sd(resid) over 252/21 | trailing 504 sessions | 504 sessions |
| RM-36 | as RM-24, paper-faithful | trailing 756 sessions | 756 sessions |

RM-24 and RM-36 are the controls. Without them we cannot tell whether
relaxing eligibility bought anything or just added noise. §5.6 of the paper
tested 24- and 60-month windows and found results "very similar", so RM-24
is sanctioned by the paper itself.

## Outcome

A decision on whether a residual score replaces MM's `voladj` score, judged
on the standing bar: the quarterly challenger protocol's **> 0.10 Sharpe
margin** over the locked rules, on the §17 grid over the trailing ten years.
A "no" that is measured is a valid and expected outcome — see the standing
stance that the production books are working and portfolio work is
diagnostic, not exploratory.

## Scope boundary

- Nothing in `tasks/mm_rebuild/MECHANICS.md` changes unless the > 0.10
  margin is cleared and the founder signs it off.
- MM only. OM25's capture ratio is already an index-relative device, so
  residualising may be partly redundant there; the clean test is on pure
  momentum. OM25 is revisited only if RM wins on MM.
- No production port. This runs on the honest master store, alongside
  `tasks/production_port_2026`, not into it.
- No new data sourcing. If the answer turns out to need HML, that is a
  finding to report, not a purchase to make.

## What we are not testing

We have no book-to-market, so the factor set is market + sector rather than
Fama-French. In large caps (Table 8) SMB was never the issue — beta −0.39,
and −0.08 after residualising — while market and value carry the load, with
HML_UP at 1.31 the largest single term. The working hypothesis is that
sector residualisation picks up much of what HML does in India, where value
has historically been heavily sector-loaded. **That is a hypothesis, not a
finding**, and it is the main reason a null result here would not settle the
question. The paper's own §5.3 found that adding industry factors on top of
FF3 reduced residual momentum's risk further, which is mild support.

## Known risks

- **Turnover is unmeasured in the paper.** They never measure it; the cost
  argument in §4.4 is indirect ("residual momentum holds bigger stocks,
  big stocks are cheaper to trade"). A regression residual is plausibly a
  noisier month-to-month ranking than a raw return. At 20 bps each way on a
  25-name monthly book this is material. G7 applies: a candidate that wins
  only on turnover-blind metrics is flagged.
- **Long-only blunts the thesis.** Every number in the paper is a D10−D1
  hedge portfolio and the whole argument is about that portfolio's factor
  betas. We are long-only: we want market beta, it is most of our return.
  Residualising the signal does not make the book market-neutral, it only
  changes which names get picked. Size expectations to that.
- **Sector cap interaction.** If the score is residualised against sector,
  the 5-per-sector cap becomes partly redundant — both devices exist to stop
  the book chasing whichever sector just ran. Worth testing a relaxed cap;
  one fewer parameter against the G6 ≤ 10 budget.
- The decade result most often quoted from this paper (total-return
  momentum −8.54% p.a. over 2000-2009 against residual momentum +4.65%) has
  t-statistics of −1.19 and 1.18. Suggestive, not established.
- Robeco productised this in 2011. Out-of-sample performance since has not
  been checked. Worth a literature pass before any adoption decision.

## Critical files

| Path | What |
|---|---|
| `lib/diag_eligibility.py` | Phase 0 diagnostic — history-requirement attrition |
| `data/master/membership/nifty250.csv` | Point-in-time universe |
| `data/master/panels/pr/` | Per-name daily price-return panels |
| `data/master/benchmarks/NIFTY_100_bench.csv` | Market factor |
| `tasks/mm_rebuild/sector/sector_v2_lookup.csv` | Sector labels, `as_of` dated |
| `tasks/mm_rebuild/MECHANICS.md` | The locked book this challenges |
| `tasks/om25_rebuild/lib/run.py` | Harness: `panels()`, `MEMBERSHIP` |
| `tasks/om25_rebuild/lib/regime.py` | `membership_mask` |
