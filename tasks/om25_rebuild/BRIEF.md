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

## ROC regime — the prior test, retrieved 2026-09-10

Source: `tasks/portfolio_risk_2026/` on branch `beta_gtm_mvp` (commit
`af4a3cb`, 2026-09-04), worktree `.worktrees/beta_gtm`. Harness
`regime_experiment.py`, results `RESULTS.md` §4-7, 12-15, verdicts `STATE.md`.

**Definition tested** (`build_regime()`):

    roc  = close / close.shift(N) - 1
    raw  = roc > 0            (risk-on)     threshold zero throughout
    regime = confirm(raw, confirm_days)      same sticky state machine as the
                                             production MA: flips only after
                                             `confirm_days` consecutive
                                             opposite readings; lagged 1 day

Grid: N in {10, 15, 21, 31, 42, 52, 63, 126, 252}, confirm in {1, 2, 3, 5, 8};
index NIFTY 100 (from 2010), NIFTY 500 (from 2015), controls.

**Result that matters here** — ROC as the *score tilt* on OM25, same index
(NIFTY 100), 16.1 years 2010-07 → 2026-08, no overlay, stop off:
ROC31/c3 33.57% CAGR / Sharpe 1.84 / MaxDD −34.5% vs MA100/c3 33.13% /
1.79 / −36.0%. ROC31 beat MA on every metric in both stop settings.
Recorded there as "the best-evidenced single change found anywhere in this
task", conditional on no exposure overlay shipping. Lookbacks ≥ 63 were
worse than nothing (ROC126 MaxDD −49%); confirm = 1 (no hysteresis) cost
3-6pp CAGR everywhere; the ROC-52 dent shows single-cell precision
exceeds the sample — read it as "about a month, with confirmation".

**Why it is a hypothesis here, not a result.** That test ran on the
survivorship-biased universe (today's members backdated) that D-13
discarded, and on a window with two bear episodes. It is re-tested on the
honest universe from 2006, which has five.

**Also in that thread, NOT in this brief unless the founder adds it:** a
separate *exposure overlay* (100% risk-on / 75% risk-off on NIFTY 100
ROC31/c3) that cut OM25's drawdown to −23% at ~3.7pp of CAGR. The brief
says "just the hysteresis"; the overlay is out of scope until said otherwise.

## Decisions 2026-09-10 (founder)

- Gates G1-G7 in TASKS.md §0 **signed as proposed**; frozen.
- "Just the hysteresis" confirmed: no per-stock stop, no portfolio drawdown
  stop. The regime confirmation hysteresis is the only risk control.
- ROC regime search: N ∈ {15, 21, 31, 42} × confirm ∈ {2, 3, 5} on NIFTY 100;
  ROC is the regime mechanic. Exposure overlay deferred to a later step.
- Market for up/down days: **(b)** equal-weight mean of the signal-date
  members' returns across the trailing window — the existing construction.
  (a) point-in-time-by-day and (c) the published index were offered and
  not chosen.
- Positive one-year-return eligibility filter: not decided; kept as a
  searchable switch, counted in the deflation.

## Constraints added 2026-09-10 (founder, after §3)

- Exposure overlay brought back into scope (§3e): the ROC regime drives
  gross exposure in bear; the engine's regime_panel / bear_exposure path,
  entries skipped in bear (engine default).
- Return filter tested as a switch.
- **Portfolio size ≤ 25 positions** — anything more is difficult to operate.
  §3c's 40-name cell is out; 25 / buffer 20 is the pick.
- **Lookback ≤ 12 months**; shorter is acceptable.
- Cadences tested so far: biweekly (§3a, §3b) and monthly (§3c, §3d);
  weekly not yet.
