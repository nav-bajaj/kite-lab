# Results — trend_screen_2026

**Verdict (final, 2026-09-13):** Shippable as one product with three parts, and the spec is frozen in `STATE.md` here. The trend classification is robust (ordering holds under all 135 threshold sets and in every era). The exit is the **profit-lock ratchet (+15% arm, keep 50%, ma150 backstop)**, chosen for the subscriber's ride and found to be the best portfolio rule as well: **24.8% / −35.5% / 0.99 OOS at 25 slots, no regime gate.** Breadth direction is a **label** on every call — improving calls returned +24% and deteriorating +5% on closed 2021+ trades, both positive — never a gate, because gating emptied a third to half of months and hurt the book three separate times. Headline statistics are **closed calls only**; the 45 open calls were flattering every number and are shown separately. Six task folders, 44 commits, and the failures are recorded beside the passes.

Opened 2026-09-11, closed 2026-09-13. Successors: `regime_allocation_2026`,
`regime_first_2026`, `trigger_calls_2026`, `exit_asymmetry_2026`.

> **The sections below are the record of this folder's own work and are
> superseded where they conflict with the verdict above.** In particular:
> the "spec, frozen" and "headline numbers" sections describe the
> composite-direction *gate* and the ma150 exit as they stood at §7; the
> shipped spec (ratchet exit, direction as a label, closed-only statistics)
> and current numbers live in **`STATE.md`** in this folder, which is the
> entry point for the whole programme.

## What was shipped vs planned

| Phase | Planned | Actual |
|---|---|---|
| §1 classifier hardening | sweep thresholds, check stability | Done — 135/135 configs hold |
| §2 the 15-second read | card content spec | **Not built** — deferred until the firing rule changes (see Follow-ups) |
| §3 entry location | pullback vs breakout, return *and* R | **Not run** — superseded by the regime work |
| §4 avoid list | ship criteria | **Not built** — the research is done, the product spec is not |
| §5 ranking and trim | does a ranking beat the list | Done — 8 of 10 candidates beat it |
| §7 expectancy + portfolio | gates P1-P7 | Done |
| §8 IS/OOS phase allocation | founder's proposal | Done, then superseded by `regime_allocation_2026` |
| §9 fill correction | not planned | Added after the founder caught it |

## The spec, frozen

Universe: top 500 by trailing 63-session median turnover **and** above the
turnover-scaled ₹10cr floor, point-in-time, survivorship-free (1,716 names,
1,134 of which stop trading before 2026).

Signal: month-end close, name is LEADING or EXTENDED — close > 50 > 150 >
200-day, 200-day above its level 21 sessions ago, ≥30% above the 52-week low,
≥75% of the 52-week high. Ranked by % above the 52-week low; top 20 are calls.

Regime gate: composite breadth (expanding-percentile mean of % above 200-day,
% in LEADING/EXTENDED, net new highs) above its level **63 sessions** ago.

Execution: buy at **OHLC/4 of T+1**, sell at **OHLC/4 of the session after**
the first close below the 150-day. 0.2% slippage. No hard stop.

## Headline numbers (production fills)

| Calls product, top 20, gated, 2014-2026 | |
|---|---|
| calls | 757 (4.9/month, 46% of months produce none) |
| win rate | 45% |
| average win / loss | +65.1% / −16.1% |
| payoff ratio | 4.05 |
| **expectancy per call** | **+20.71%** |
| median call | −4.3% |
| median hold | 91 sessions |
| negative years | 4 of 13 (2015, 2018, 2019, 2024) |

| Portfolio, 25 slots, equal weight | 2006-2026 | OOS 2016-2026 |
|---|---|---|
| CAGR | 21.1% | 23.9% |
| max drawdown, marked daily | −37.3% | −37.2% |
| Sharpe | 0.95 | 1.02 |
| era Sharpes | 0.44 / 0.81 / 1.60 | — |
| always-on control, same fills | 20.3% / −48.1% / 0.73 | 17.2% / −40.5% / 0.56 |

Capacity holds: 28.9% at ₹25cr over 2020-2026, 14.3% at ₹100cr. This is the
decisive difference from `breakout_calls_2026`, whose edge died at size.

## Gate outcome

| | target | result | |
|---|---|---|---|
| P1 CAGR | ≥18% | 21.1% | pass |
| P2 max DD | ≥−35% | −37.3% | **fail** |
| P3 Sharpe | ≥0.80 | 0.95 | pass |
| P4 era Sharpe | ≥0.50 each | 0.44 / 0.81 / 1.60 | **fail** (2006-2012) |
| P6 capacity | ₹25cr | 28.9% | pass |
| deflation (G7, from successor task) | beat Gumbel bound | inside noise | **fail** |

Three fails, one story: the full-period result leans on 2020-2026.

## Findings worth carrying forward

1. **Thresholds do no work.** 135/135 configurations preserve the state
   ordering; spread range 5.6-6.2%. Do not tune; freeze and never present a
   tuned number.
2. **Confirmation filters hurt on both axes.** Requiring a state to persist
   lowers expectancy *and* raises turnover.
3. **EXTENDED is a tag, not a state** — 25% persistence, 74% of runs last one
   month. Best-performing condition, least durable category.
4. **Ranking is one factor** — the four best rankers correlate 0.73-0.89;
   "how far the name has already run". Time-in-state is the only negative.
5. **Hit rate against the index is 47-48% at every cut**; on raw returns it is
   56-59%. The first is the honest alpha claim, the second is what a
   subscriber banks. Do not conflate them.
6. **Dropping off the buy list costs ~3pp over six months** — removals are
   substantive and must be acted on.
7. **Entering the list is weaker than being on it** (+2.7% vs +3.9% at 6m).
   A "new this month" feature would highlight the weakest slice.

## Blocked / not done

- §2 (the 15-second read), §3 (entry location), §4 (avoid list ship spec).
  All three are live and worth doing; none were run.

## Follow-ups — founder direction 2026-09-13

- **Month-end firing is an artifact**, not a design choice: the features table
  was built as monthly snapshots for compute. A calls product should fire on a
  stock-level trigger. Consequence measured: the regime signal flips **26
  times a year** raw (median run 3 sessions) and month-end sampling hides it.
  Trigger-based firing samples that signal far more often, so **hysteresis
  becomes mandatory** — N=5 sessions cuts flips to 4.6/yr at identical time-on
  (47%).
- **The 150-day trail is under-tested.** §4 of the predecessor swept only
  ma50 / ma150 / chandelier(3×ATR). Untested: other ATR multiples,
  swing-low structure stops, volatility-scaled trails, profit ladders.
- **Process inversion** — define regimes first from market structure alone,
  then fit setups per regime. New task, see `regime_first_2026`.
