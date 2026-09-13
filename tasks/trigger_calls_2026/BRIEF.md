# Agent brief — trigger_calls_2026

Read: this file, PLAN.md, TASKS.md, then
`tasks/trend_screen_2026/lib/features.py` (95 lines — you are extending it)
and `tasks/breakout_calls_2026/lib/exits.py` (140 lines — `load_panel`,
`simulate`). Nothing else. Do not explore.

## Budget and conduct
- Repo root `/Users/navdeep/kite-lab`, `source .venv/bin/activate`.
- The daily build touches ~1,716 symbols × ~5,000 sessions. Write it as one
  background script that streams per-symbol frames to a list and concatenates
  once; expect ~5 min. Do not hold a wide panel — long format only.
- Report once, in RESULTS.md. If a step fails, record it under "Blocked" and
  continue with what does not depend on it.
- Edit nothing outside `tasks/trigger_calls_2026/` except `exits.py` if a new
  trail type is needed (additive, absent → unchanged). Do not commit.

## Interfaces — exact

```python
import sys
sys.path.insert(0, "tasks/trend_screen_2026/lib"); sys.path.insert(0, "tasks/breakout_calls_2026/lib")
from features import classify            # classify(df) -> Series of state labels; df needs close,s50,s150,s200,s200_21,hi52,lo52
from exits import load_panel, simulate   # load_panel(sym) -> dict(dates,pos,o,h,l,c,s50,s150,atr); simulate(p,e,entry,stop0,cfg)
from book import build_book, era_sharpe
```

`simulate(p, e, entry, stop0, cfg)` with
`cfg=dict(stop_mode="fixed", stop_pct=0.99, trail="ma150", partial_r=None, timestop=None, atr_mult=3.0, exec_ohlc4=True)`
returns `(ret, r, hold, reason)`. `e` is the ENTRY bar index; set
`entry = (o[e]+h[e]+l[e]+c[e])/4 * 1.002` where `e = trigger_bar + 1`.
`exec_ohlc4=True` makes the trail exit fill at OHLC/4 of the session after the
signal. For a `stop0` use `entry*0.01` (no hard stop). For ATR trails use
`trail="chandelier"` with `atr_mult` ∈ {2,3,4}. For ma100 and swing-low you
add a branch to `simulate` — additive, keyed on a new `trail` value.

**Universe eligibility**: `tasks/breakout_calls_2026/data/pit_universe.parquet`
cols `date, symbol, adv, eligible`; drop duplicates on (symbol,date); rank
`adv` descending per date; eligible universe = rank ≤ 500 AND `eligible`.

**Breadth**: `tasks/trend_screen_2026/data/breadth.parquet`, daily index,
col `pct_above_200`.

**Benchmark/calendar**: `data/master/benchmarks/NIFTY_500.csv` cols
`date, close`. Calendar from its dates.

**Reference tape to reproduce for A1**:
`tasks/trend_screen_2026/data/calls_full_range_ohlc4.csv` — build T3 by
sampling your daily table at each symbol's last session per (year, month),
top-20 by `above_low` among LEADING/EXTENDED, and it must match §7's
757 / 45% / +20.71% for 2014-2026 with the hysteresis gate.

Alpha per call: `bench.asof(entry_date)` and `bench.asof(exit_date)`.

## RESULTS.md template
```
# Results — trigger_calls_2026
**Verdict:** <trigger, gain/cost vs month-end, does the persistent gate help>
## A1 reproduction  <yes/no, numbers>
## Regime gate  <flips/yr, median run, time-on>
## Per-call, all triggers × gate  <one table, T3 rows included>
## Cadence  <one table>
## Entry timing and overlap  <T1 vs T3>
## Exit sweep  <grid median, best, Gumbel, per-era>
## Portfolio  <best config vs always-on, full span + OOS>
## Blocked
## Follow-ups
```
Tables over prose. Percentages one decimal, Sharpe two.
