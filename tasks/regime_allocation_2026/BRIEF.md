# Agent brief — read this, then PLAN.md and TASKS.md, then start

You are executing `tasks/regime_allocation_2026`. Everything you need is
named below with its exact interface. **Do not explore the repo, do not read
other task folders, do not re-derive anything that is stated here.** The
infrastructure exists and works; your job is to run the experiments in
TASKS.md and write RESULTS.md.

## Budget

- Run from repo root `/Users/navdeep/kite-lab` with `source .venv/bin/activate`.
- Long runs go in the background; one `build_book` call on 7,828 trades takes
  ~20-40 s. §2's grid is ≤ 60 candidates × 2 (rule + control) × 3 seeds; run
  it as one script that writes a CSV, not 60 interactive calls.
- Report **once**, at the end, via RESULTS.md. No progress narration. If a
  step fails, write the error into RESULTS.md under "Blocked" and continue
  with the next step that does not depend on it.
- Do not edit any file outside `tasks/regime_allocation_2026/` except the one
  additive change to `book.py` specified in TASKS §1 (the `force_exit`
  parameter). Do not commit.

## What exists — use exactly these

```python
import sys
sys.path.insert(0, "tasks/breakout_calls_2026/lib")
sys.path.insert(0, "tasks/trend_screen_2026/lib")
from book import build_book, era_sharpe
from exits import load_panel
```

**`build_book(trades, panels, calendar, slots, risk_pct, max_weight, adv_cap,
capital, seed, order, regime) -> dict`**
- `trades` needs columns `symbol, entry_date, exit_date, entry, exit_px, stop,
  adv, final_depth`; optional `wt` (per-trade multiplier, 0 = skip).
- `panels` is `{symbol: {"close": pd.Series indexed by date}}`.
- `calendar` is a `DatetimeIndex` of sessions — build it from
  `data/master/benchmarks/NIFTY_500.csv` `date` column, never from symbols.
- Use `slots=25, risk_pct=1.0, capital=1e7, order="tight"` — this makes
  positions equal-weight 1/N. `final_depth` is the sort key (lower first);
  set it to `rnk`.
- Returns `equity` (daily Series), `dd`, `cagr`, `maxdd`, `sharpe`, `taken`,
  `exposure`, `passed_full`, `passed_cash`, `passed_adv`.
- `regime` is an optional `pd.Series[date -> bool]`; False blocks new entries
  that day. You will mostly use `wt` instead.

**`load_panel(sym) -> dict | None`** with keys `dates, pos, o, h, l, c, s50,
s150, atr`. Build `panels` as
`{s: {"close": pd.Series(p["c"], index=p["dates"])} for s, p in loaded.items()}`.

**The tape** — `tasks/trend_screen_2026/data/calls_full_range.csv`, 7,828
rows, columns `symbol, entry_date, exit_date, entry, ret, bench_ret, alpha,
hold, rnk, state, phase, pct_above_200, pct_above_200_chg, open`. To make it
book-ready:
```python
tr = pd.read_csv(TAPE, parse_dates=["entry_date","exit_date"])
tr["exit_px"] = tr.entry * (1 + tr.ret)
tr["stop"] = tr.entry * 0.01
tr["final_depth"] = tr.rnk
pit = pd.read_parquet("tasks/breakout_calls_2026/data/pit_universe.parquet",
                      columns=["date","symbol","adv"]).drop_duplicates(["symbol","date"])
tr = tr.merge(pit, left_on=["symbol","entry_date"], right_on=["symbol","date"], how="left")
tr["adv"] = tr.adv.fillna(tr.adv.median()); tr = tr.drop(columns=["date"])
```
This is exactly what `tasks/trend_screen_2026/lib/run_isos.py` does — read
that file once; it is 110 lines and is the harness you are extending.

**Breadth** — `tasks/trend_screen_2026/data/breadth.parquet`, daily, indexed
by date, columns `n, pct_above_200, at_high, at_low, net_highs,
pct_above_200_chg, net_highs_chg, phase`. `phase` is the current four-bucket
label. For signal A2 (`pct_leading`) compute from
`tasks/trend_screen_2026/data/features_t500_ranked.parquet` (month-end rows,
column `state`) as the share in `{"LEADING","EXTENDED"}` per date, then
forward-fill to daily. For A4 (`pct_above_50`) add a `c > s50` flag to
`breadth.symbol_flags` and re-run `breadth.build` — it takes ~3 min.

**The breakout tape** for §4's cross-signal check —
`tasks/breakout_calls_2026/data/book_trades.csv`, already book-ready
(has `exit_px, stop, adv, final_depth`).

## Reference numbers you must reproduce before §2

Founder's rule, `pct_above_200`, window 63, median cut, four buckets
{EXPANSION 1, RECOVERY 1, TOPPING 0.5, CONTRACTION 0}, OOS 2016-2026:
**CAGR 21.6%, maxDD 36.7%, Sharpe 0.92.** Always-on same span: 19.1% / 41.0%
/ 0.66. Half-everywhere control: 13.5% / 26.4% / 0.64. If you cannot get
within 0.3pp / 0.5pp / 0.02 of these, stop and write what you got.

## Walk-forward, precisely

For year Y in 2014..2026: fit window is `[Y-8, Y-1]` entry dates. For every
cell in the candidate's parameter grid, run the book on the fit window and
take the cell with the highest Sharpe. Apply that cell to entries in year Y.
Chain the yearly equity segments (each year starts from the prior year's end
equity). Report chained CAGR / maxDD / Sharpe and the per-year table of chosen
cells. Always-on and the exposure control are walked the same way (they have
no parameters, so "fit" is trivial, but the chaining must match).

## RESULTS.md template — fill every section, keep it this shape

```
# Results — regime_allocation_2026

**Verdict:** <one sentence: a rule passed G1-G7 / none did; name it or the closest miss>

## Gate table
| candidate | G1 | G2 | G3 | G4 | G5 | G6 | G7 | pass |
(one row per §3 candidate, values not just ticks)

## §1 smoke test
reproduced: <yes/no> — <your numbers vs reference>

## §2 grid (IS/OOS)
trials: <N>  grid median OOS Sharpe: <x>  best: <x> (<cell>)  Gumbel E[max]: <x>
candidates beating always-on OOS: <k of N>
<table: top 10 by (OOS Sharpe − control Sharpe), with IS and OOS and control>

## §3 walk-forward
<table: candidate | WF CAGR | WF maxDD | WF Sharpe | static OOS Sharpe | cells chosen (distinct) | G1..G7>
<per-year picks for the best one>

## §4 robustness
<alternate splits, where-the-rule-acts, slots, cross-signal — one small table each>

## §5 cost
<time in cash, turnover, changes/yr, worst whipsaws, tax drag>

## Blocked
<anything that failed, with the error>

## Follow-ups
<bullets — things that wanted a new signal/exit/universe; do not run them>
```

Numbers to one decimal for percentages, two for Sharpe. Every table has the
always-on row. Prefer a table to a paragraph everywhere.
