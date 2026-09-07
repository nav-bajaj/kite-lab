# STATE — minimum_capital_2026

**Read this first.** Status as of 2026-09-06.

## Where it landed

**Phase 1 (capital + SIP): answered, ready to use.**
Suggest **Rs 5L minimum / Rs 10L recommended**, with **Rs 10k/month floor
and Rs 25k/month recommended** SIP on a Rs 10L base. Rs 1-5L is the wrong
band — its bottom is structurally broken. Full arithmetic in `RESULTS.md`.

**Phase 2 (price cap): answered, decision open.**
A Rs 4,000 per-share entry cap would move the minimum ticket from
~Rs 10L to ~Rs 2L. Cost, per portfolio:

| portfolio | net effect of the cap | verdict |
|---|---|---|
| COMBO Defensive | +0.18pp CAGR, MaxDD -16.4% -> -14.7% | cleanest on numbers; carries a structural forced-exit risk |
| OM25 v3 | +0.72pp CAGR | free; grandfathers winners properly |
| L6 v2 | **-1.35pp CAGR, MaxDD -29.9% -> -33.9%** | a real cost |

## What is decided

- Rs 1-5L is rejected as a suggested band. Rs 5-10L is the answer for the
  books as they stand today.
- The cap, if adopted, gates **entry only**. Forced exit on breach is
  rejected: it sells exactly the winners a momentum strategy exists to
  hold (OM25 evidence: 4.3-4.4% of realised P&L accrues above the cap).
- Rs 2,000 as a cap is rejected. Its apparent edge is real but is an
  in-sample low-price/size tilt that **reversed in 2024 and 2026**.
- A fixed nominal cap is rejected as a permanent design. Rs 4,000 was the
  94th percentile of the Nifty 250 in 2021 and is the 84th today; blocked
  names rose from 6.4% to 16.3% of the universe. Tie it to the advertised
  ticket (`cap = (min_capital / 25) / k`) or to a universe percentile,
  and review annually.

## What is open — founder decision

1. **Adopt the cap, and for which portfolios?** Not asked and not
   assumed. COMBO and OM25 are close to free; L6 costs ~1.3pp CAGR.
2. **COMBO's architecture.** COMBO structurally cannot grandfather a
   winner through the cap (`make_combo_score_fn` emits exactly 24 names
   at exit_buffer 0; a holding that appreciates through the cap is sold
   at the next rebalance — median 6 days, 71% within 21 days). If COMBO
   is capped, this wants fixing first.
3. **TL25 v3 was not tested.** It holds expensive names (NEULANDLAB
   Rs 23,301) and turns over fast; do not assume the result carries.
4. **Publishing framing** — see the flags at the end of `RESULTS.md`.

## Known limitation that constrains any re-run

The price panel is **split/bonus back-adjusted** (verified: IRCTC's 1:5
split, ex 2021-10-29, shows no discontinuity in `nse500_data`). Historic
panel prices are therefore *lower* than what actually traded for any name
that later split — and expensive names are the likeliest to split. So the
cap was **more permissive in the backtest than it would have been live**,
and the historical blocking rate is understated. Direction known,
magnitude not: only the VEDL 2026-04-30 demerger is tracked in
`data/corporate_actions.json`. This affects any future study keyed on
price levels, not just this one.

## Scripts, in run order

| script | what it does | runtime |
|---|---|---|
| `capital_sizing.py` | Phase 1. Cost drag, replication feasibility, share granularity, SIP deployability. | ~20s |
| `om25_cap_sweep.py` | OM25 baseline + cap sweep (Rs 1k-12k). | ~15s/arm |
| `om25_cap_placebo.py` | Random-exclusion control for OM25. The null that makes the sweep interpretable. | ~13s/seed |
| `l6_combo_cap_study.py` | L6 + COMBO baseline, capped arm, and both placebos. | ~25 min at 30 seeds |
| `price_decile_study.py` | Forward return by price decile, and by year. Explains the placebo result. | ~3 min |
| `forced_exit_audit.py` | Days held after crossing the cap, and P&L above it, per arm. Reads `runs/*trades*.csv`. | ~30s |

Outputs land in `runs/`. Every headline number in `RESULTS.md` and
`RESULTS_PRICE_CAP.md` is regenerable from these six scripts.

## Method note worth carrying forward

The cap sweep alone is uninterpretable — it is non-monotonic, and reading
its best arm as "the optimum" would have picked Rs 2,000 and shipped an
unintended small-cap bet. **The random-exclusion placebo is what made the
result readable**, by separating "excluding names costs opportunity"
(it does, 1.2-3.4pp) from "excluding *expensive* names costs extra"
(it does not). Use the same control for any future universe-restriction
study.
