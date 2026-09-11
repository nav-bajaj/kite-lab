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

## OM25 — "Quality Momentum", Nifty 250 (fixed rules, founder decision 2026-09-11: the blended score on the MM stack)

| Element | Rule |
|---|---|
| Universe | NIFTY LARGEMIDCAP 250, point-in-time membership |
| Score | rank blend: 40-50% vol-adjusted momentum (252 sessions ending 21 before the signal, / annualised vol, floor 5%) + 50-60% capture ratio (upside vs downside participation over the same 252 sessions, positive window return required); **weight fixed at 50/50** (founder 2026-09-11; §21: plateau 40-60) |
| Eligibility | ≥ 220 priced sessions in the window |
| Signal / execution | close of the first trading day of each month; next-session execution |
| Book | up to 25 names; entrants by rank from the top 45; exit below rank 45; after a bear the book rebuilds as positions exit; no trimming |
| Sizing | inverse-volatility (63-day), capped at 10%; positions drift |
| Sector cap | at most 5 names per NSE sector at entry |
| Regime and bear behaviour | NIFTY 100 ROC31, 3-day confirmation, prior close; in bear the book holds ≤ 15 names, exits at rank 35 |
| Stop | 20% trailing from peak, checked at the monthly signal, executed next session |
| Rhythm | **one order day a month** |
| Parameters | 10 (as MM plus the blend weight) — G6 ≤ 10 |
| Record | static 2016-26: 24.9% / 1.21 / −29%; Wright window 34.3% / 1.65, up-capture 1.09 / down 0.70; single-book process (§22) 19.8% / 0.93 / −30% — plan on the process band |
| Monitoring and forward gate | as MM: quarterly §22 grid on trailing ten years, 0.10 margin, founder sign-off; rolling 3-year Sharpe ≥ 0.6, drawdown ≥ −40%, judged quarterly from 2026-10-01 |
| Retired | the yearly refit process of om25_rebuild §4b and its 2026 pick (50/50 UC+CR, buffer 10, weekly stop: 0.82, up 1.29 / down 1.14) |

## Where they differ

The two books share every device and differ only in the score: MM is pure
vol-adjusted momentum (the aggressive version, up-capture 1.10 / down 0.77),
OM25 blends it with the capture ratio (up 1.09 / down 0.70, better
2016-19 and 2023-26, weaker 2020-22). Monthly correlation 0.86; 14 of
about 22 names in common on 2026-09-11.
