# Exit asymmetry — keep more of what the call already earned

## The problem, measured (closed calls, 2021-2026, T3 top-20, ma150 exit)

| | |
|---|---|
| calls that were up >10% at some point | 66% |
| of those, closed at a loss | 38% |
| median peak open gain → median banked | **+44% → +7%** |
| median share of peak gain kept | **20%** |
| median sessions from peak to exit | 41 |
| calls that peaked >20% up and closed negative | 47 (10% of all) |

The 150-day trail is a *level* rule: the stock must fall all the way to a
slow average before the call closes. For a name that has run 40% in three
months that average is a long way down, and the tape pays for the whole
journey back.

**Age is informative, and not in the obvious direction.** By when the peak
came:

| peak came | n | median peak | median banked | share kept |
|---|---|---|---|---|
| < 1 month | 197 | +4% | −16% | — |
| 1-2 months | 59 | +17% | −8% | — |
| 2-3 months | 42 | +33% | +1% | 4% |
| 3-6 months | 103 | +54% | +17% | 29% |
| > 6 months | 75 | +115% | +64% | 58% |

Trades that peak early give everything back; trades that peak late keep
half. So there are **two distinct failures**: the young call that pops and
fades (the thesis did not hold), and the mature call that runs and then
returns a long way (the thesis held and the exit was slow). One exit rule
cannot serve both. That is the founder's two-phase instinct, and the data
supports it.

An upper bound on the prize: a floor at 50% of peak gain, armed once the
call is up 20%, with no other change, moves expectancy **+13.6% → +19.4%**
and win rate **41% → 51%** — assuming the floor fills exactly, which it will
not.

## What is fixed

Everything except the exit: T3 month-end trigger, top 20, top-500 + floor
universe, OHLC/4 fills both sides, 0.2% slippage, one position per name.
Tape: `tasks/trigger_calls_2026/data/tapes.parquet`, `kind == "T3"`, `rk <= 20`,
de-duplicated to one open position per name. **Full span 2006-2026 is the
basis**; 2021-2026 closed-only is reported alongside but nothing is chosen on
it.

## Pre-registered exit families — eight, nothing added afterwards

Each family is a complete exit. Every one is evaluated with and without the
ma150 as a backstop (whichever fires first).

| # | Family | Parameters | The idea |
|---|---|---|---|
| X0 | ma150 (reference) | — | what the tape uses now |
| X1 | **profit-lock ratchet** | arm at +A ∈ {15, 25}%; keep k ∈ {50, 65}% of peak gain | a floor that only rises; the give-back is capped as a share of what was earned |
| X2 | **armed chandelier** | arm at +A ∈ {15, 25}%; then exit below peak − m×ATR20, m ∈ {3, 5} | a peak-based trail that does not exist until the call has earned it |
| X3 | **age-scaled trail** | ma150 for the first N ∈ {42, 63} sessions, then ma50 | the founder's two-phase rule in its simplest form |
| X4 | **thesis time-box** | if not up ≥ Y ∈ {5, 10}% by session N ∈ {42, 63}, exit; otherwise ma150 | kills the pop-and-fade young call; touches nothing that is working |
| X5 | **state exit** | exit when the name leaves LEADING/EXTENDED (daily state from `daily.parquet`) | the screen's own definition of "thesis over" — non-price, no parameter |
| X6 | **rank exit** | exit when the name falls outside the top R ∈ {50, 100} by % above 52w low | the reason for the call was rank; losing it is the reason to leave |
| X7 | **two-phase composite** | X4 (N=42, Y=5) for the young call, then X1 (A=25, k=60) once mature | the founder's proposal as one rule |
| X8 | **regime-tightened X1** | X1 (A=25, k=60), but k rises to 75 when breadth direction is deteriorating | let the market label change how much give-back is tolerated |

Trial count: X0 + 8 + 4 + 2 + 4 + 1 + 2 + 1 + 1 = 23 cells, ×2 for the
ma150 backstop variant on X1-X8 = ~45. The Gumbel expected max of that many
draws is reported beside the best.

## Gates — pre-committed

A family is a candidate only if, on the **full span 2006-2026**:

| # | Criterion | Value |
|---|---|---|
| E1 | expectancy vs X0 | ≥ +2.0pp |
| E2 | median share of peak gain kept (on calls that reached +10%) | ≥ 35% (X0 is ~20%) |
| E3 | average winner vs X0 | ≥ 85% of X0's — it must not win by clipping the tail |
| E4 | per-era expectancy | positive in all three, none below 60% of the full-span figure |
| E5 | 2021-2026 closed-only expectancy vs X0 on the same basis | ≥ +2.0pp — the out-of-family check |
| E6 | best cell clears the Gumbel bound of the trials run | yes |

Turnover and median hold reported for every cell. A rule that halves hold
time is a different product and is flagged, not celebrated.

## Not in scope

New entries, new universe, new ranking, partial exits (already shown to hurt
on this tape when fixed at +nR — X7's time-conditioning is the one exception
and it is a full exit, not a partial), and anything that requires intraday
data.
