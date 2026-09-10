# Brief — founder constraints, 2026-09-10 (verbatim, do not paraphrase away)

> We'll run both universes. Because we now need to decide fresh which one
> works best. Regime - instead of ma I want it to be ROC instead. We tested
> it out recently in another thread. No max weight cap. No per stock SL,
> just the hysteresis. Also remove the 50 up and down days requirement.
> Also for score we now need to test 100% UC, 100% CR and 50-50 blend.
> And also test whether we do one regime or two. Since we're starting from
> scratch we need to build the strategy up again.

Earlier the same day: baseline accepted from 2020 onwards; the old
portfolio was tuned on a different universe membership set, so nothing of
its parameters is carried over (market_data_spine D-13). Price return is
the basis (D-12).

## Read as

| Constraint | Reading | Open? |
|---|---|---|
| Both universes | every candidate runs on Nifty LargeMidcap 250 AND Nifty 500 (point-in-time files in `data/master/membership/`); the universe is itself a decision the gates make | no |
| Regime = ROC | rate-of-change of the index replaces close-vs-MA; definition and lookback from the prior thread's test (being retrieved) | pending retrieval |
| No max weight cap | equal 1/N at entry, no 7.5% cap, positions drift | no |
| No per-stock SL, "just the hysteresis" | no trailing stop, no portfolio drawdown stop; the regime's confirmation hysteresis is the only risk control | **confirm** |
| Remove 50 up/down days | eligibility is min_obs only (and the positive-return filter unless told otherwise) | no |
| Score variants | 100% UC, 100% CR, 50/50 blend — three candidates | no |
| One regime or two | (a) one score always; (b) bull/bear tilt between two scores — tested, not assumed | no |
| From scratch | no parameter inherits; every value chosen by the gates | no |

## Data

Master store only (`data/master/`): `panels/pr/` (price-return view),
`membership/{nifty250,nse500}.csv`, `benchmarks/NIFTY_100.csv` (regime
index, Kite, 2003→), `benchmarks/NIFTY_100_bench.csv`. Nothing reads
`nse500_data*` or `data/static/`.
