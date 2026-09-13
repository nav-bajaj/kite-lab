# Agent brief — exit_asymmetry_2026

You already hold everything this needs from trigger_calls_2026: the T3 tape,
`daily.parquet` (daily state per name), `load_panel`, `simulate`, the OHLC/4
fill convention, and the breadth series. Read PLAN.md here, then start. Do
not re-read other task folders.

## Basis
- Tape: `tasks/trigger_calls_2026/data/tapes.parquet`, `kind=="T3"`, `rk<=20`,
  then one open position per name (skip a signal whose name's previous call
  has not exited). This is the 1,828-call full-span tape; 2021+ closed-only
  should land near 476 calls / 41% / +13.6% under X0 — confirm that first.
- Every exit fills at OHLC/4 of the session AFTER the exit condition is met,
  +0.2% slippage, same as the entry.
- "Peak" = highest close since entry. "Up +A%" is measured on close vs entry.
- X5 needs the daily state: join `daily.parquet` on (symbol, date).
- X6 needs the daily rank: `rk` per (symbol, date) is in `daily.parquet` if
  you wrote it; if not, recompute % above 52w low rank among LEADING/EXTENDED
  per date from the same file.
- X8 needs breadth direction: `d = pct_above_200 − pct_above_200.shift(63)`,
  21-session mean, from `tasks/trend_screen_2026/data/breadth.parquet`;
  deteriorating = d ≤ 0.

## Reporting
One table, every cell (with and without ma150 backstop), columns:
family | params | backstop | n | win | avg win | avg loss | expectancy | alpha |
median hold | share of peak kept | 2021+ closed exp | E1..E6 pass.
Then per-era for the top 5. Then the Gumbel line. Then, for the best cell
that clears E1-E6 (if any), the 2021+ closed-only call list under that exit
next to X0's for the same calls — so the founder can see what changed trade
by trade. Save as `data/exit_grid.csv` and `data/best_vs_x0_2021.csv`.

RESULTS.md in `tasks/exit_asymmetry_2026/`, verdict first: which family, what
it keeps, what it costs, and whether it clears E6. No narration, no commit,
write only in this folder (plus additive branches in exits.py if needed).
