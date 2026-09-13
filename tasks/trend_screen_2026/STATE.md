# Trend-calls programme — state as of 2026-09-13

Read this first. Six task folders, 44 commits (`a30d59a`..HEAD), one product.
Everything below is on production fills (OHLC/4 of T+1, 0.2%), the top-500
survivorship-free universe, and closed trades unless stated.

## The frozen spec

| | |
|---|---|
| Universe | top 500 by trailing 63-session median turnover AND above the turnover-scaled ₹10cr floor, point-in-time; delisted names carried (1,134 of 1,716 stop before 2026) |
| Signal | last session of each month; name is LEADING/EXTENDED — close > 50 > 150 > 200-day, 200-day above 21 sessions ago, ≥30% above 52w low, ≥75% of 52w high |
| Rank | % above the 52-week low; top 20 are the calls; a name already held is not re-issued |
| Label | **improving** if % of universe above its 200-day exceeds its level 63 sessions ago, on a 21-session mean; else **deteriorating**. Read at the signal; never gates |
| Entry | OHLC/4 of the next session, +0.2% |
| **Exit** | **once up 15% on close, exit if close < entry × (1 + 0.5 × peak gain); otherwise first close below the 150-day; whichever first. Fill at OHLC/4 of the session after, −0.2%** |
| Book | 25 slots equal-weight, 10% ADV participation cap, no gate |

## What it does

| | calls product (2021-26, closed) | portfolio (25 slots) |
|---|---|---|
| win / expectancy | 55% / +10.4% per call, median call +4.9% | — |
| by label | improving +24%, deteriorating +5% (both closed) | — |
| cadence | 7.6 calls/month, 0% empty months | — |
| CAGR / DD / Sharpe | — | 2006-26: 22.2% / −46.6% / 0.87 · OOS 2016-26: **24.8% / −35.5% / 0.99** |
| era Sharpes | — | 0.61 / 0.56 / 1.47 |
| capacity | — | ~29% at ₹25cr over 2020-26 (ma150 basis; ratchet not re-run at size) |

## What passed, what failed — by folder

| folder | question | answer |
|---|---|---|
| `breakout_calls_2026` | competitor audit; is VCP breakout a product | Their 64.5% is a realised-only drawdown and a survivor universe. VCP has a real per-trade edge (0.47R) and **fails 5 of 7 portfolio gates** — edge lives in microcaps, dies at ₹25cr |
| `trend_screen_2026` | does trend state predict, is it a product | **Yes.** Ordering holds 135/135 thresholds, all eras. Basket not stock-picker (47% hit rate vs index). Ranking is one factor. Confirmation filters hurt. EXTENDED is a tag |
| `regime_allocation_2026` | can a breadth gate be walked forward | **No rule passes.** Best clears 6/7, fails deflation; IS→OOS rank correlation of 69 rules is −0.002 |
| `regime_first_2026` | define regimes first, from structure only | k-means k=2 clears R1-R3 and real-time test (median run 78d, 1.9 flips/yr). **Nothing leads** — best lags peaks 22d, troughs 46d. Asymmetric divergence was the worst candidate |
| `trigger_calls_2026` | fire on triggers not month-end | **Month-end wins per call** — it is a 21-session confirmation filter; 48% of trigger episodes never confirm and return +2.8%. ma150 survives its sweep. Persistent gate helps the call, **hurts the book**; asymmetric (slow-off/fast-on) fixes the book but only on drawdown. **Direction beats level** as a label, +20.7% vs +16.2%, persistence free |
| `exit_asymmetry_2026` | keep more of the peak | Per call, **nothing beats ma150** (60 cells). Re-ranked by ride, the +15/50 ratchet gives 55% winners for 5pp; **as a book it beats ma150 on every metric** |

## Corrections made along the way — keep these

- Fill convention: tapes used next-open / signal-close; production is OHLC/4 T+1. Fixed via opt-in flag. Cost 0.2-0.4pp/call, ~3pp portfolio CAGR.
- Universe: a pure top-750 rank admitted ₹0.03cr/day names in 2006; the floor is required. Clean universe made the portfolio *better*.
- Open calls: 45 open calls at the 9-Sep mark inflated 2021+ expectancy from +13.6% to +17.4%. Headline is closed-only, always.
- One-position-per-name: a tape re-firing every held name inflated 2021+ to 1,426 calls; 521 is correct.
- Regime charts: weekly-resampled phase bands hid 16 flips/yr. The raw signal dithers (median run 3-4d) because the *threshold* dithers, not the market — 79% of days sit in runs >60d.
- Un-backstopped exits are not exits: nine "winning" cells held 330-559 sessions and never closed 11-18% of calls.
- Upper bounds on floors assumed exact fills; a momentum name gapping through a floor turns +5.8pp into −2.7pp.

## Open

- **The labelled-calls artifact still shows the ma150 exit.** Rebuild on the ratchet.
- Capacity for the ratchet book at ₹25cr+ (ma150 basis was fine; not re-run).
- `trend_screen_2026` §2 (the 15-second read), §3 (entry location), §4 (avoid-list ship spec) — all live, none run.
- A 12-month frozen paper test is the only test left that the sample cannot contaminate.
- Second products sketched (2026-09-13): hold-the-list basket, 200-day slow trail, improving-only tier, avoid-list standalone, pullback entries.
