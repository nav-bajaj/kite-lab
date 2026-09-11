# The two books as on 2026-09-11

Both run on the honest master store (price return, point-in-time
membership), net of 20 bps slippage each way. Both are research books;
neither is in production.

## MM — "MoMo", Nifty 250 (fixed rules, TASKS.md decision 2026-09-11)

| Element | Rule |
|---|---|
| Universe | NIFTY LARGEMIDCAP 250, point-in-time membership |
| Score | vol-adjusted momentum: return over the 252 sessions ending 21 sessions before the signal date, divided by annualised daily vol over the same window, floored at 5% |
| Eligibility | ≥ 219 priced sessions in the window; no other filter |
| Signal / execution | close of the first trading day of each month; orders at the next session's trade price |
| Book | up to 25 names; entrants are drawn by rank from the top 45 (`fill_from_buffer`, 2026-09-11); a holding exits at the monthly review if its rank falls below 45 (25 + buffer 20); after a bear the book rebuilds over the following rebalances as positions exit — no position is ever trimmed to make room (trimming sells the winners, §19) |
| Sizing | inverse-volatility across the intended book (63-day vol), capped at 10%; positions drift, never resized |
| Sector cap | at most 5 names per NSE sector at entry (21 sectors; historical labels in `sector/`) |
| Regime | NIFTY 100 31-session rate of change, sign, 3-day confirmation to flip, decided from the prior close |
| Bear behaviour | entries capped so the book holds ≤ 15 names; exits at rank 35; the top names stay fully sized; residual cash tolerated |
| Stop | 20% trailing from the position's peak, checked at the monthly signal, executed next session |
| Rhythm | **one order day a month**; no weekly action |
| Parameters | 9 (universe, lookback, skip, top-N, buffer, sizing cap, sector cap, bear N, stop) — G6 ≤ 10 |
| Record | static 2016-26: 25.2% / 1.15 / −27% with fill-from-buffer (25.7% / 1.18 without; top of a 128-cell grid); process band 20-21% / 0.85-0.90 / −31% (§17-§17b) — plan on the band |
| Monitoring | quarterly report: §17 grid on trailing ten years; a challenger must beat the standing rules by > 0.10 Sharpe to be raised; changes are the founder's call, phased over 1-2 rebalances |
| Forward gate | rolling 3-year Sharpe ≥ 0.6, drawdown ≥ −40%, judged quarterly from 2026-10-01 |

## OM25 — "Quality Momentum", Nifty 250 (adaptive process, om25_rebuild §4b; decision on fixing it pending)

| Element | Rule |
|---|---|
| Universe | NIFTY LARGEMIDCAP 250, point-in-time membership |
| Score, current pick (2026) | 50/50 blend of upside-capture rank and capture-ratio rank over the trailing 252 sessions; market = equal-weight members; positive window return required; one regime (no tilt) |
| Signal / execution | close of the first trading day of each month; next-session execution |
| Book | 25 names, equal weight at entry, no cap; exit at the monthly review below rank 35 (25 + buffer 10, current pick) |
| Stop | 20% trailing from peak, **checked weekly** (Friday close, Monday execution) — the monthly check costs 0.1 Sharpe here (§5b) |
| Regime / overlay | none (fully invested) |
| Rhythm | one order day a month plus an occasional Monday stop sale; ~2 action days a month |
| Process | each January the configuration with the best trailing five-year Sharpe among score {CR, 50/50, UC} × regimes {1, 2} × buffer {0, 10, 20} × stop {off, 20%} is traded; picks 2024-26: 50/50, 1 regime, buffer 10-0-10, stop 20% |
| Record | chained 2016-26: 21.6% / 0.90 / −35%, sub-windows 0.88 / 0.99 / 0.91; chained 2011-26: 21.4% / 0.97 |
| Open | whether to fix the rules as MM did (the process changed six times in eleven years, mostly stop and score) and the forward gate |

## Where they differ

MM is vol-adjusted price momentum with the risk devices; OM25 is the
capture-ratio family with a refit. Monthly correlation between the two
is high (both Nifty 250 momentum); the blend question is open.
