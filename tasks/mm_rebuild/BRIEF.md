# Brief — founder constraints, 2026-09-10 (verbatim, do not paraphrase away)

> Let's move to the core momentum portfolio, where we track momentum and
> price performance instead of a capture ratio. So I guess it'll be a
> version of the L6 portfolio. Let's call it the MoMo portfolio, or MM.
> We'll have to develop it in the same format. We just did the OM25
> portfolio. [...] Let's start with the new portfolio with two universes:
> 250 and 500, with a look back of 6 months, 9 months, and 12 months.
> Absolute momentum and volatility-adjusted momentum. Then we'll keep on
> adding filters and devices to optimize.

## Read as

| Constraint | Reading | Open? |
|---|---|---|
| Same format as OM25 | task folder, gates pre-committed before the first search, every trial registered, IS 2010-2015, OOS 2016→ opened once, honest master store, price return, 20 bps slippage | no |
| A version of L6 | production L6 v2 is `momentum_6m / max(realized_vol, 5%)`, top 24, weekly; nothing of its parameters is inherited (spine D-13), the formula family is | no |
| Two universes | Nifty LargeMidcap 250 and Nifty 500, point-in-time membership; the universe is a decision the gates make | no |
| Lookbacks 6 / 9 / 12 months | 126 / 189 / 252 sessions, min_obs at 87% | no |
| Absolute momentum | trailing lookback price return | no |
| Volatility-adjusted momentum | trailing return / annualised daily volatility over the same window, floor 5% (L6's form) | no |
| Filters and devices later | skip-month, positive-momentum eligibility, exit buffer, cadence, stop, regime tilt, exposure overlay — each a later section, each counted | later |

Carried from OM25 unless the founder says otherwise: 25 positions, equal
weight, no weight cap, monthly entry and exit, exit buffer 20, no stop, fully
invested. These are the §1 mechanics, not decisions; §2 onward searches them.

## Data

Master store only. Same harness as `tasks/om25_rebuild/lib` (imported, not
copied); runs and registry under `tasks/mm_rebuild/runs/`.
