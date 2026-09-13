# Trigger-based calls

## Why

`trend_screen_2026` fires a call on the last session of each month. That is
an artifact of how the feature table was built (monthly snapshots, for
compute), not a property of the signal. A subscriber product fires when the
stock's own condition triggers. This task rebuilds the tape on that basis and
measures what changes.

Two things are expected to change and both must be reported, not assumed:
cadence (calls per month, share of empty months) and entry timing (a trigger
catches a name the day it qualifies; month-end catches it up to 21 sessions
later, or misses it if it has already left the state).

## What is fixed

| Fixed | Value |
|---|---|
| Universe | top 500 by trailing turnover + scaled ₹10cr floor, PIT, survivorship-free |
| State | LEADING / EXTENDED per `trend_screen_2026/lib/features.py::classify`, default thresholds |
| Rank | % above the 52-week low, top 20 |
| Fills | OHLC/4 of T+1, both sides, 0.2% slippage |
| Reference exit | first close below the 150-day, no hard stop |
| Regime gate | **hysteresis 40/60 on % above the 200-day** — the persistent form; the raw direction switch is not used here because it flips 26 times a year |

## Triggers under test — pre-registered

- **T1 state-entry**: the session a name moves INTO {LEADING, EXTENDED} from any other state, and is top-20 by rank that session. One call per episode; a name that leaves and re-enters is a new episode.
- **T2 rank-entry**: the session a name already in {LEADING, EXTENDED} first enters the top 20 by rank. One call per rank-episode.
- **T3 month-end (control)**: the existing rule. Must reproduce `trend_screen_2026` §7 on the same tape.

Regime gate applied to all three as a variant; no-gate is the control.

## Exit sweep — bounded

Only after the trigger comparison is recorded. Five exits, no partials, no
time stops: ma150 (reference), ma100, ATR trail at 2× / 3× / 4× ATR20 below
the running high, swing-low structure stop (last confirmed ±5-bar pivot low).
Report grid median, best cell, and the Gumbel expected max of 5 draws.

## Non-negotiables

- Daily classification, not monthly. The feature build emits every session.
- Point-in-time throughout. A trigger on day T uses T's close; the regime
  gate on day T uses T's breadth; the fill is T+1.
- One position per name at a time.
- Realised-only drawdown is never computed.
- Nothing is tuned on the trigger comparison. T1/T2/T3 are three fixed
  definitions, reported side by side.
