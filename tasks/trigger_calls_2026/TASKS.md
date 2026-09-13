# Tasks

Owners: 👤 founder · 🤖 agent.

## §0 — what is reported, and the one gate

This task is measurement, not selection. Every table has the T3 month-end
control row. One gate:

| # | Criterion | Value |
|---|---|---|
| A1 | T3 reproduces `trend_screen_2026` §7 top-20 gated 2014-2026: 757 calls, 45% win, +20.71% expectancy | within 5 calls / 1pp / 0.5pp |

If A1 fails, the daily build is wrong; stop and report.

## §1 — daily feature build 🤖

- [ ] `lib/daily_features.py`: same indicators as `features.py`, every session,
      per symbol, written as one long parquet `data/daily.parquet` with columns
      `date, symbol, close, s50, s100, s150, s200, s200_21, hi52, lo52, state,
      above_low`. Restrict to universe-eligible (date, symbol) pairs.
- [ ] Cross-sectional rank per date on `above_low` among LEADING/EXTENDED →
      column `rk`.
- [ ] Regime series: `pct_above_200` from `trend_screen_2026/data/breadth.parquet`,
      hysteresis enter ≥0.60 / exit <0.40, as a date→bool series. Record its
      flips/yr and median run (expect ~1.6 and ~99).

## §2 — the three tapes 🤖

- [ ] Emit T1, T2, T3 call tapes: `symbol, trigger_date, entry_date, entry,
      exit_date, exit_px, ret, hold, rk, state_at_trigger, gate_on`.
- [ ] **Gate A1** on T3.
- [ ] Per-call table for each trigger × {gate on, no gate}: n, win, avg win,
      avg loss, ratio, expectancy, alpha vs NIFTY 500 over the hold, median,
      median hold, per-era (2006-12 / 13-19 / 20-26).
- [ ] Cadence per trigger: calls/month mean and median, share of zero months,
      busiest month, longest empty run.
- [ ] Entry timing: for names caught by both T1 and T3, days between the two
      entries and the return difference — this is what month-end was costing.
- [ ] Overlap: share of T1 calls that T3 never fired (left the state before
      month-end).

## §3 — exit sweep on the winning trigger 🤖

- [ ] Five exits per PLAN, on the trigger with the best gated expectancy.
- [ ] Grid median, best, Gumbel E[max of 5], per-era for the best.

## §4 — portfolio check 🤖

- [ ] Best trigger × reference exit × gate, 25 slots equal-weight, daily MTM,
      2006-2026 and OOS 2016-2026, with the always-on control. Reuse
      `breakout_calls_2026/lib/book.py`.

## §5 — RESULTS.md 🤖

Template in BRIEF.md. Verdict line first: which trigger, what it costs or
gains against month-end, and whether the persistent gate helps.
