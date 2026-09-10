# Results — the two call strategies, unchanged, on the honest store

Store: `data/master/panels/pr` (price return, from 2005), point-in-time
membership for NSE 500 and Nifty 250, loaded through the OM25 harness
(`tasks/om25_rebuild/lib/run.py`). Slippage 20 bps each way. One run per
strategy per universe, 2010-01-01 → 2026-09-09 (store end), frozen
parameters, no search: four runs plus two sensitivity runs of one
interpreted rule (§7), all reported. Sharpe at rf 5% unless marked. Windows
and helpers as in `tasks/om25_rebuild/lib/windows.py`; capture and legs as
in `tasks/mm_rebuild/RESULTS.md` §7 (MidSmall 400 synthetic series).

## §0 — the rules, as published

### Stage-2, final configuration "S2-v2" (branch `stage2_portfolio`, RESULTS.md Addendum 2)

Quoted from that document:

> **Gate (hard pass/fail, all seven must hold on the signal date):**
> 1 Close > 150 DMA and Close > 200 DMA; 2 150 DMA > 200 DMA; 3 200 DMA
> rising over the last 20 trading days; 4 50 DMA > 150 DMA (full stack);
> 5 Close > 50 DMA; 6 Close >= 1.30 x 52-week low; 7 Close >= 0.75 x
> 52-week high — plus RS >= 70th percentile (126-day return, ranked across
> the point-in-time universe).
>
> **S2-v2.** Your spec, unchanged: RS + un-extension score (0.5/0.5), 20
> names, no sector cap, drift, no stop, no stage-age minimum. Three changes
> to the exit only:
> - **Hold gate tiered.** Entry still needs all seven conditions plus RS >=
>   70. Holding needs only the structure: above the 150 and 200 DMA, 50 >
>   150 > 200, 200 DMA rising. Slipping under the 50 DMA or out of the top
>   quartile of the 52-week range no longer forces a sale.
> - **Exit confirmation 3 weeks.** A name is sold only after it fails the
>   keep test on N consecutive weekly checks, rather than the first time.
> - **Exit buffer 40** (keep set = top 60 rather than top 30).
>
> **Mechanics:** weekly Friday signal to next-day OHLC/4, equal 1/N capped
> at 7.5%, 20 bps slippage.

Un-extension is `1 - percentile(close / 50 DMA - 1)` among the day's
eligible names; RS is the percentile of the 126-day return. Score = 0.5 x
un-extension + 0.5 x RS, both percentiles taken among gate-passers plus
current holdings that still pass the tiered hold gate. The engine is the
branch's `s2_engine.py`, carried verbatim into `lib/s2.py` (the production
`scripts/_clean_engine.py` has neither exit confirmation nor an entry gate
separate from the hold gate; equivalence in the degenerate case is checked
in §6). Code: `git show stage2_portfolio:tasks/stage2_portfolio/lib/{stage2,s2_engine,run_s2,lineup}.py`;
the configuration dict `S2V2` in `lineup.py` is what ran here.

### Dip-timed momentum feed "dip25_ts20" (`tasks/dip_vs_breakout_calls`, RESULTS.md and `experiment.py`)

Quoted from that document:

> Window 2010-06 → 2026-08-19, NSE 500 minus 33 cliff-artifact symbols,
> top-quartile 126d momentum filter, momentum-rank slot priority, exit at
> momentum rank < 0.35, next-day OHLC/4 ± 20bps.
> **dip25_ts20 is the headline arm**: 25 slots, entry timer "5-day return
> < -5%", 20%-from-peak trail.

As coded in `experiment.py`: momentum score = (close / close 126 sessions
ago − 1) / max(annualised 126-day daily-return vol, 5%), percentile-ranked
across the universe each day (`build_score_rank`); entry signal when the
5-day close-to-close return is below −5% and the rank is >= 0.75, one call
per symbol, candidates filled by rank descending until 25 are active; exit
when the rank is below 0.35 at any close, else when the close is below 80%
of the highest close since the signal day; every fill the next session at
OHLC/4, plus 20 bps on entry and minus 20 bps on exit. Portfolio curve =
25 equal slots, idle slots earn zero.

### What the port changes, and only this

1. Universe: point-in-time members of the master-store membership files
   (`nse500.csv`, `nifty250.csv`). Both cross-sectional ranks (S2's RS
   percentile, the dip feed's momentum rank) are taken across that day's
   members. A held name that leaves the index is grandfathered: for S2 it
   drops out of scoring, as the branch code did, and is sold after the
   three-strike confirmation; for the dip feed it is ranked against the
   day's members (share of member scores below it) so its exit rule keeps
   working. Neither can re-enter while a non-member.
2. Data: the master store forward-fills a delisted name flat at its last
   price (the store's delist-at-LTP convention, shared with the OM25 and MM
   rebuilds). S2's strict inequalities fail on a flat series and it is sold
   at that price; a dip-feed holding's momentum decays to the exit rank.
3. Window: 2010-01-01 → 2026-09-09 as one path (the branch S2 restarted
   each window; the dip study started 2010-06-01 and ended 2026-08-19).
   Like-for-like windows are in §8.
4. The dip feed's headline curve is built from actual fills (slot marked
   from its entry fill, exit at its exit fill); the branch's `slot_curve`
   used raw close-to-close returns, gross of slippage. That gross curve is
   also computed on the honest panel and reported beside it.
5. S2 runs without volume (the RS + un-extension score and the gate do not
   use it) and without a sector map (cap 0 in S2-v2).

Interpretation stated for the record: the branch's RS percentile was ranked
across every alive column of its own panel; the rule as written says "the
point-in-time universe", which is what ran. The other basis is §7.

## §1 — headline windows

| Strategy | Universe | IS 2010-15 | OOS 2016-26 | 2016-19 | 2020-22 | 2023-26 | Wright Oct-20 to Aug-26 | Calls/month |
|---|---|---|---|---|---|---|---|---|
| Stage-2 (S2-v2) | NSE 500 | 13.2% / 0.48 / -23.9% | **14.9% / 0.49 / -35.7%** | 8.8% / 0.21 / -23.8% | 25.7% / 0.90 / -34.8% | 13.4% / 0.44 / -31.6% | 16.7% / 0.59 / -31.6% | 6.0 |
| Stage-2 (S2-v2) | Nifty 250 | 14.7% / 0.62 / -27.3% | **15.3% / 0.53 / -35.8%** | 8.7% / 0.23 / -23.4% | 21.1% / 0.71 / -35.8% | 18.1% / 0.68 / -27.9% | 20.5% / 0.79 / -27.9% | 4.7 |
| Dip feed (dip25_ts20) | NSE 500 | 22.9% / 1.04 / -29.1% | **22.2% / 0.85 / -34.3%** | 9.6% / 0.25 / -25.0% | 40.3% / 1.45 / -34.3% | 22.9% / 0.95 / -30.5% | 29.3% / 1.19 / -30.5% | 5.2 |
| Dip feed (dip25_ts20) | Nifty 250 | 20.3% / 0.97 / -27.8% | **18.0% / 0.70 / -32.7%** | 13.8% / 0.56 / -17.6% | 29.9% / 1.14 / -32.7% | 13.5% / 0.46 / -23.7% | 20.7% / 0.84 / -23.7% | 4.5 |
| MM base (mm_rebuild §9) | NSE 500 | - | **21.7% / 0.78 / -34%** | 0.57 | 1.51 | 0.37 | 21.1% / 0.74 / -34% | 14.6 (trades) |
| MM base (mm_rebuild §9) | Nifty 250 | - | **19.7% / 0.73 / -38%** | 0.49 | 1.12 | 0.65 | 26.2% / 1.03 / -30% | 7.0 (trades) |

MM base rows are `tasks/mm_rebuild/RESULTS.md` §9 (NSE 500: vol-adjusted
6m, skip 21, monthly, 25 names; Nifty 250: 12m). Their last column is
trades per month, not calls.

Dip feed, the branch's gross slot curve (raw closes, no slippage) on the same honest panel, for comparison with the earlier 37.8% / 1.65:

| Universe | IS 2010-15 | OOS 2016-26 | 2016-19 | 2020-22 | 2023-26 | Full 2010-26 |
|---|---|---|---|---|---|---|
| NSE 500 | 24.2% / 1.12 / -28.3% | 24.3% / 0.95 / -34.3% | 11.4% / 0.35 / -22.9% | 43.2% / 1.57 / -34.3% | 24.7% / 1.04 / -29.2% | 24.3% / 1.00 / -34.3% |
| Nifty 250 | 21.5% / 1.04 / -26.1% | 19.4% / 0.78 / -32.6% | 15.3% / 0.66 / -16.8% | 31.4% / 1.21 / -32.6% | 14.6% / 0.52 / -22.6% | 20.1% / 0.86 / -32.6% |

## §2 — up / down capture vs MidSmall 400

| Strategy | Universe | Wright window up | down | beats index in up / down months | Long run 2011-26 up | down |
|---|---|---|---|---|---|---|
| Stage-2 (S2-v2) | NSE 500 | 0.88 | **1.07** | 56% / 57% | 0.84 | 0.74 |
| Stage-2 (S2-v2) | Nifty 250 | 0.99 | **1.14** | 49% / 48% | 0.85 | 0.73 |
| Dip feed (dip25_ts20) | NSE 500 | 1.16 | **1.17** | 56% / 43% | 1.05 | 0.78 |
| Dip feed (dip25_ts20) | Nifty 250 | 0.97 | **1.05** | 44% / 39% | 0.91 | 0.65 |
| MM base | NSE 500 | 1.09 | 1.37 | 58% / 35% | 1.08 | 0.80 |
| MM base | Nifty 250 | 1.09 | 1.11 | 51% / 52% | 0.94 | 0.66 |
| Wright (ex-costs) | - | 1.11 | 0.90 | 62% / 57% | - | - |

## §3 — leg returns

| Book | bull Apr-20 to Oct-21 | bear Oct-21 to Jun-22 | bull Jun-22 to Sep-24 | bear Sep-24 to Feb-25 | bull Feb-25 to Aug-26 | Calendar 2021 |
|---|---|---|---|---|---|---|
| MidSmall 400 | 132.0 | -12.4 | 124.3 | -22.0 | 27.4 | 51.3 |
| Stage-2 (S2-v2), NSE 500 | 123.4 | -7.6 | 107.3 | -27.8 | 16.6 | 28.8 |
| Stage-2 (S2-v2), Nifty 250 | 86.7 | -6.0 | 140.4 | -24.1 | 23.0 | 27.1 |
| Dip feed (dip25_ts20), NSE 500 | 148.6 | -3.9 | 170.6 | -26.7 | 27.3 | 79.2 |
| Dip feed (dip25_ts20), Nifty 250 | 106.6 | -9.1 | 119.3 | -22.3 | 12.5 | 56.7 |
| MM base, NSE 500 | 158 | -5 | 143 | -29 | 9 | 69.7 |
| MM base, Nifty 250 | 106 | 1 | 124 | -25 | 38 | 56.8 |

## §4 — trade-level statistics

| Strategy | Universe | Calls | Calls/month | Open at end | Win rate | Avg winner | Avg loser | Expectancy | Median call | p5 / p95 | Calls > +50% | Hold median / mean (cal days) | Hold median / mean (sessions) | Exits by stop / rule | Open book mean P&L |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Stage-2 (S2-v2) | NSE 500 | 1190 | 6.0 | 20 | 52.1% | 20.6% | -13.2% | 4.4% | 1.0% | -24.9% / 40.9% | 2.9% | 77 / 90 | 54 / 61 | 0.0% / 100.0% | 12.0% |
| Stage-2 (S2-v2) | Nifty 250 | 942 | 4.7 | 20 | 50.7% | 22.5% | -11.3% | 5.8% | 0.3% | -20.9% / 46.0% | 4.2% | 98 / 123 | 68 / 84 | 0.0% / 100.0% | 19.3% |
| Dip feed (dip25_ts20) | NSE 500 | 1036 | 5.2 | 25 | 45.5% | 42.6% | -13.6% | 12.0% | -2.3% | -22.2% / 82.7% | 11.3% | 108 / 145 | 72 / 99 | 68.6% / 31.4% | 41.1% |
| Dip feed (dip25_ts20) | Nifty 250 | 898 | 4.5 | 25 | 47.2% | 37.3% | -11.7% | 11.4% | -1.1% | -21.2% / 76.7% | 10.3% | 126 / 168 | 86 / 114 | 52.5% / 47.5% | 10.6% |

Book shape: Stage-2 (S2-v2) NSE 500 mean holdings 17.5, invested 87.8%, under 50% invested 7.1% of days; Stage-2 (S2-v2) Nifty 250 mean holdings 19.0, invested 95.5%, under 50% invested 0.4% of days; Dip feed (dip25_ts20) NSE 500 mean holdings 24.9, at cap 97.7% of days; Dip feed (dip25_ts20) Nifty 250 mean holdings 24.8, at cap 88.5% of days.

Calls = one entry of one symbol. Expectancy = mean net P&L per closed call.
"Rule" exits are the momentum-rank exit for the dip feed and the keep-set
exit for S2, split there into names that had also left the tiered hold
gate ("gate") and names that were only out of the top 60 ("rank"); S2-v2
has no stop, so its stop share is zero by construction.

## §5 — by calendar year of entry

### By calendar year of entry: Stage-2 (S2-v2), NSE 500

| Year | Calls | Win rate | Avg winner | Avg loser | Expectancy | Median hold (cal days) | Exits by stop | Portfolio return |
|---|---|---|---|---|---|---|---|---|
| 2010 | 102 | 52.0% | 14.3% | -11.6% | 1.9% | 63 | 0.0% | 26.7% |
| 2011 | 58 | 37.9% | 27.7% | -11.7% | 3.3% | 119 | 0.0% | -9.0% |
| 2012 | 53 | 60.4% | 19.3% | -9.2% | 8.0% | 98 | 0.0% | 34.4% |
| 2013 | 56 | 51.8% | 20.3% | -16.3% | 2.6% | 92 | 0.0% | -4.4% |
| 2014 | 80 | 63.7% | 23.1% | -12.1% | 10.3% | 74 | 0.0% | 38.0% |
| 2015 | 69 | 33.3% | 16.8% | -13.8% | -3.6% | 91 | 0.0% | 8.9% |
| 2016 | 66 | 57.6% | 16.3% | -15.8% | 2.6% | 71 | 0.0% | -11.3% |
| 2017 | 99 | 64.6% | 19.1% | -10.1% | 8.8% | 70 | 0.0% | 60.8% |
| 2018 | 74 | 35.1% | 19.3% | -13.3% | -1.9% | 91 | 0.0% | -13.3% |
| 2019 | 50 | 38.0% | 15.4% | -15.1% | -3.5% | 105 | 0.0% | 14.4% |
| 2020 | 60 | 66.7% | 46.8% | -15.5% | 26.0% | 94 | 0.0% | 52.0% |
| 2021 | 72 | 54.2% | 20.0% | -11.3% | 5.7% | 70 | 0.0% | 28.8% |
| 2022 | 74 | 39.2% | 18.4% | -15.4% | -2.2% | 91 | 0.0% | 1.4% |
| 2023 | 87 | 74.7% | 19.6% | -9.2% | 12.3% | 70 | 0.0% | 39.3% |
| 2024 | 70 | 47.1% | 18.1% | -13.5% | 1.4% | 63 | 0.0% | 30.1% |
| 2025 | 70 | 45.7% | 14.7% | -16.2% | -2.1% | 84 | 0.0% | -21.9% |
| 2026 | 50 | 50.0% | 17.5% | -12.8% | 2.3% | 77 | 0.0% | 11.7% |

Exit mix (closed calls): rank 648, gate 522. Store end 2026-09-09.

### By calendar year of entry: Stage-2 (S2-v2), Nifty 250

| Year | Calls | Win rate | Avg winner | Avg loser | Expectancy | Median hold (cal days) | Exits by stop | Portfolio return |
|---|---|---|---|---|---|---|---|---|
| 2010 | 85 | 55.3% | 16.3% | -11.1% | 4.1% | 77 | 0.0% | 32.1% |
| 2011 | 58 | 39.7% | 13.0% | -10.7% | -1.3% | 102 | 0.0% | -19.7% |
| 2012 | 44 | 61.4% | 18.6% | -11.5% | 7.0% | 105 | 0.0% | 34.3% |
| 2013 | 47 | 46.8% | 35.4% | -13.5% | 9.4% | 133 | 0.0% | -1.5% |
| 2014 | 67 | 70.1% | 22.9% | -11.0% | 12.8% | 77 | 0.0% | 38.8% |
| 2015 | 55 | 36.4% | 16.0% | -11.7% | -1.6% | 98 | 0.0% | 22.7% |
| 2016 | 51 | 62.7% | 19.6% | -12.5% | 7.7% | 120 | 0.0% | -2.1% |
| 2017 | 66 | 53.0% | 24.3% | -10.8% | 7.8% | 105 | 0.0% | 43.6% |
| 2018 | 51 | 23.5% | 14.3% | -9.5% | -3.9% | 126 | 0.0% | -15.5% |
| 2019 | 34 | 35.3% | 12.1% | -10.6% | -2.6% | 171 | 0.0% | 18.0% |
| 2020 | 40 | 80.0% | 40.5% | -17.0% | 29.0% | 134 | 0.0% | 25.8% |
| 2021 | 75 | 52.0% | 17.2% | -10.0% | 4.2% | 84 | 0.0% | 27.1% |
| 2022 | 46 | 39.1% | 41.8% | -14.1% | 7.7% | 130 | 0.0% | 11.3% |
| 2023 | 57 | 68.4% | 29.0% | -7.7% | 17.4% | 99 | 0.0% | 33.0% |
| 2024 | 77 | 49.4% | 20.2% | -13.4% | 3.2% | 77 | 0.0% | 48.7% |
| 2025 | 58 | 33.9% | 14.9% | -9.4% | -1.1% | 120 | 0.0% | -13.4% |
| 2026 | 31 | 38.5% | 14.6% | -14.1% | -3.1% | 98 | 0.0% | 7.6% |

Exit mix (closed calls): gate 544, rank 378. Store end 2026-09-09.

### By calendar year of entry: Dip feed (dip25_ts20), NSE 500

| Year | Calls | Win rate | Avg winner | Avg loser | Expectancy | Median hold (cal days) | Exits by stop | Portfolio return |
|---|---|---|---|---|---|---|---|---|
| 2010 | 75 | 46.7% | 35.5% | -14.9% | 8.6% | 99 | 72.0% | 41.7% |
| 2011 | 72 | 41.7% | 41.9% | -14.0% | 9.3% | 120 | 63.9% | -13.9% |
| 2012 | 44 | 50.0% | 23.5% | -11.8% | 5.8% | 146 | 61.4% | 45.5% |
| 2013 | 53 | 43.4% | 41.4% | -13.5% | 10.3% | 126 | 60.4% | 1.2% |
| 2014 | 56 | 71.4% | 50.3% | -10.1% | 33.0% | 134 | 58.9% | 81.3% |
| 2015 | 51 | 39.2% | 26.0% | -15.3% | 0.9% | 109 | 64.7% | 13.0% |
| 2016 | 67 | 61.2% | 31.5% | -15.5% | 13.3% | 142 | 50.7% | -1.5% |
| 2017 | 35 | 54.3% | 33.6% | -10.6% | 13.4% | 119 | 77.1% | 62.9% |
| 2018 | 80 | 35.0% | 18.5% | -13.5% | -2.3% | 112 | 85.0% | -19.3% |
| 2019 | 46 | 30.4% | 23.9% | -12.2% | -1.2% | 112 | 78.3% | 12.5% |
| 2020 | 80 | 56.2% | 104.3% | -16.2% | 51.6% | 111 | 63.7% | 50.5% |
| 2021 | 61 | 47.5% | 40.2% | -13.2% | 12.2% | 101 | 75.4% | 79.2% |
| 2022 | 94 | 43.6% | 40.2% | -14.4% | 9.4% | 82 | 79.8% | 2.5% |
| 2023 | 42 | 73.8% | 58.7% | -10.7% | 40.5% | 140 | 47.6% | 65.4% |
| 2024 | 54 | 33.3% | 24.6% | -13.2% | -0.6% | 90 | 77.8% | 37.2% |
| 2025 | 93 | 23.5% | 21.1% | -13.3% | -5.2% | 66 | 68.2% | -15.1% |
| 2026 | 33 | 25.0% | 24.0% | -11.0% | -2.3% | 76 | 75.0% | 11.3% |

Exit mix (closed calls): ts20 694, momq 317. Store end 2026-09-09.

### By calendar year of entry: Dip feed (dip25_ts20), Nifty 250

| Year | Calls | Win rate | Avg winner | Avg loser | Expectancy | Median hold (cal days) | Exits by stop | Portfolio return |
|---|---|---|---|---|---|---|---|---|
| 2010 | 65 | 47.7% | 23.5% | -12.1% | 4.8% | 121 | 63.1% | 36.2% |
| 2011 | 64 | 40.6% | 26.1% | -11.9% | 3.6% | 137 | 45.3% | -20.9% |
| 2012 | 42 | 52.4% | 33.9% | -8.3% | 13.8% | 118 | 50.0% | 39.1% |
| 2013 | 47 | 48.9% | 64.2% | -12.9% | 24.9% | 142 | 59.6% | 9.0% |
| 2014 | 47 | 63.8% | 46.0% | -9.0% | 26.1% | 154 | 42.6% | 59.0% |
| 2015 | 34 | 35.3% | 18.8% | -12.7% | -1.6% | 164 | 64.7% | 22.2% |
| 2016 | 64 | 64.1% | 33.0% | -11.2% | 17.1% | 146 | 34.4% | 4.8% |
| 2017 | 38 | 50.0% | 36.3% | -8.5% | 13.9% | 157 | 50.0% | 45.2% |
| 2018 | 59 | 44.1% | 19.1% | -14.1% | 0.6% | 139 | 67.8% | -4.5% |
| 2019 | 35 | 45.7% | 16.8% | -11.5% | 1.5% | 126 | 74.3% | 15.4% |
| 2020 | 69 | 66.7% | 58.4% | -15.9% | 33.6% | 131 | 46.4% | 34.9% |
| 2021 | 61 | 42.6% | 34.3% | -12.1% | 7.7% | 121 | 54.1% | 56.7% |
| 2022 | 73 | 42.5% | 57.0% | -11.8% | 17.4% | 105 | 53.4% | 3.3% |
| 2023 | 38 | 68.4% | 45.7% | -6.4% | 29.2% | 138 | 21.1% | 46.2% |
| 2024 | 54 | 25.9% | 21.2% | -12.0% | -3.4% | 93 | 70.4% | 23.1% |
| 2025 | 71 | 33.3% | 20.7% | -11.4% | -0.7% | 110 | 47.0% | -7.9% |
| 2026 | 37 | 5.9% | 18.6% | -12.0% | -10.2% | 96 | 52.9% | -3.2% |

Exit mix (closed calls): ts20 458, momq 415. Store end 2026-09-09.

## §6 — self-checks

Script `lib/selfcheck.py`; output quoted.

1. **Truncation.** Signal date 2019-06-28 (a Friday). Both strategies'
   panels rebuilt from a close panel cut at that date and compared with the
   full-panel values at that date. S2: 151 scored names on NSE 500, 98 on
   Nifty 250, scores identical, gate passers 69 / 69 and 41 / 41. Dip feed:
   momentum ranks identical, dip signals 16 / 16 and 7 / 7. Nothing at a
   signal date reads past it. Membership at a date is the membership file's
   effective-dated row set as of that date (built by `market_data_spine`,
   not re-verified here).
2. **Execution lag.** S2: 2,364 and 1,868 fills, none on a Friday; 92.7% /
   91.6% of fills have a Friday as the previous session, the remainder a
   Thursday where the Friday was a holiday (`fridays()` takes the last
   session of each week). Dip feed: entry session minus signal session is
   exactly 1 for every call on both universes.
3. **Engine.** With confirmation 1, strict hold gate, drift, no stop, the
   carried S2 engine and `scripts/_clean_engine.run_strategy` run the same
   score on NSE 500 over 2010-2013: end equity 1,185,376 vs 1,188,186, max
   0.8% apart on any day, 1,949 vs 1,933 fills. Cause (`lib/extra.py`):
   the percentile score ties on every date, `sort_values` and `nlargest`
   order tied names differently, and the top-20 *set* differs on 13 of 208
   signal dates. Same rule, different tie-break; not a rule difference.
4. **Cost accounting.** Every P&L in §4-§5 is exit fill x 0.998 over entry
   fill x 1.002; the S2 equity path books both sides of slippage in cash,
   the dip curve in each slot's marks.

## §7 — sensitivity of the one interpreted rule (2 runs, reported not adopted)

S2 with the RS percentile taken across every column with a price that day
(the branch code's construction; on the master store this includes
delisted names carried flat), against the main run (members only):

| Universe | Basis | IS 2010-15 | OOS 2016-26 | OOS 2017-26 | Calls |
|---|---|---|---|---|---|
| NSE 500 | members (main) | 13.2% / 0.48 / -23.9% | 14.9% / 0.49 / -35.7% | 18.1% / 0.66 / -35.7% | 1,190 |
| NSE 500 | alive columns | 11.5% / 0.37 / -25.5% | 17.6% / 0.62 / -35.1% | 19.8% / 0.74 / -35.1% | 1,202 |
| Nifty 250 | members (main) | 14.7% / 0.62 / -27.3% | 15.3% / 0.53 / -35.8% | 17.3% / 0.64 / -35.8% | 942 |
| Nifty 250 | alive columns | 14.7% / 0.61 / -26.8% | 15.7% / 0.56 / -32.4% | 17.7% / 0.66 / -32.4% | 936 |

One to three points either way, opposite signs in IS and OOS on NSE 500.
The read in §8-§9 does not depend on it.

## §8 — like-for-like against the earlier numbers

### Stage-2

The branch reported S2-v2 on NSE 500 only, IS 2010-01-04 → 2016-12-31 and
OOS 2017-01-01 → 2026-08-21 as separate runs, Sharpe at rf 0. Same
windows cut from this task's one path (`lib/extra.py`):

| Basis | IS 2010-16 CAGR / DD / Sharpe (rf 0) | OOS 2017-26 CAGR / DD / Sharpe (rf 0) | 2020+ | Median hold | Turnover |
|---|---|---|---|---|---|
| Snapshot (branch, current constituents) | 27.56% / -23.37% / 1.54 | 32.04% / -35.50% / 1.56 | 34.01% / -35.71% / 1.57 | 77d | 3.6x |
| Branch "survivorship-free" (reconstructed, 854 of 1,020 priced) | 16.53% / -28.07% / 0.91 | 25.57% / -34.56% / 1.28 | 24.27% / -34.15% / 1.15 | 84d | 3.5x |
| **Honest store, NSE 500 (this task)** | **9.3% / -24.8% / 0.51** | **18.1% / -35.7% / 0.92** | **18.6% / -34.8% / 0.89** | 77d | 3.6x |
| Honest store, Nifty 250 (this task) | 12.1% / -27.3% / 0.75 | 17.3% / -35.8% / 0.89 | 19.4% / -35.8% / 0.93 | 98d | 2.8x |

At rf 5% the honest NSE 500 OOS Sharpe is 0.66, 2020+ 0.65.

Read: the branch measured survivorship at ~15pp on the snapshot → its
reconstructed basis. Against the master store the gap is **14pp on OOS
CAGR (32.0% → 18.1%) and 18pp in-sample (27.6% → 9.3%)**, and the branch's
own "survivorship-free" basis was still 7pp optimistic out of sample (25.6%
→ 18.1%) — consistent with its 166 unpriced symbols and an RS rank taken
against a survivor-heavy panel. The hold-time fix carried over intact
(77-98 day median holds, 3-4x turnover, 51-52% win rate), the drawdown did
not: -35.7% OOS is TL25/L6 territory, not the -28% to -31% the branch
reported. S2's sub-window Sharpes (0.21 / 0.90 / 0.44 on NSE 500) are below
the MM base in every window.

### Dip feed

The study reported NSE 500 minus 33 cliff symbols, 2010-06-01 → 2026-08-19,
on the gross slot curve; a later healed-data re-run on the full current
universe gave 36.91% / 1.77 / -35.9%. Same window here:

| Basis | Full 2010-06 → 2026-08-19 | Tail 2023-07+ | IS 2010-16 | 2017-19 | 2020-22 | 2023-26 |
|---|---|---|---|---|---|---|
| Study (current constituents, gross slot curve) | 37.8% / 1.65 / -34.6% | 37.2% / 1.49 | 30.3% / 1.45 / -24.7% | 25.8% / 1.15 / -20.2% | 59.0% / 2.18 / -35.2% | 36.1% / 1.46 / -24.3% |
| Honest store NSE 500, gross slot curve | 24.5% / 1.01 / -34.3% | 22.7% / 0.90 / -29.2% | 21.0% / 0.90 / -28.3% | 15.2% / 0.60 / -22.9% | 43.2% / 1.57 / -34.3% | 24.7% / 1.04 / -29.2% |
| **Honest store NSE 500, net of fills** | **22.7% / 0.92 / -34.3%** | 20.7% / 0.80 / -30.5% | 19.5% / 0.82 / -29.1% | 13.4% / 0.50 / -25.0% | 40.3% / 1.45 / -34.3% | 22.9% / 0.95 / -30.5% |
| Honest store Nifty 250, net of fills | 19.4% / 0.82 / -32.7% | 13.6% / 0.45 / -23.7% | 18.9% / 0.86 / -27.8% | 16.7% / 0.80 / -17.6% | 29.9% / 1.14 / -32.7% | 13.5% / 0.46 / -23.7% |

Trade statistics on the same window, NSE 500: 61.2 calls/yr, win 45.0%,
mean +11.8%, median −2.4%, p5 / p95 −22.2% / +81.3%, median hold 72
sessions, 69% of exits on the trail — against the study's 58.5 / 51.6% /
+20.1% / +1.1% / −21.2% / +120.7% / 76 / 67%.

Read: **13pp of the 37.8% was survivorship (37.8% → 24.5% on the same
gross construction), another 1.8pp is slippage the published curve never
charged (24.5% → 22.7%); Sharpe 1.65 → 0.92.** The shape of the feed is
intact — flow (~5 calls a month), hold time (~3.5 months), the trail doing
two-thirds of the exits — but the per-call economics are not: win rate
falls from 52% to 45%, the median call turns negative, the p95 winner
shrinks from +121% to +81%, and the expectancy halves (+20% → +12%). What
the biased universe supplied was the right tail: today's constituents
were, by construction, the dips that recovered.

## §9 — against the MM base rows

| Universe | Book | OOS 2016-26 | 16-19 / 20-22 / 23-26 | Wright window | Up / down | Calls or trades per month |
|---|---|---|---|---|---|---|
| NSE 500 | MM base | 21.7% / 0.78 / -34% | 0.57 / 1.51 / 0.37 | 21.1% / 0.74 / -34% | 1.09 / 1.37 | 14.6 |
| NSE 500 | Dip feed | 22.2% / 0.85 / -34% | 0.25 / 1.45 / 0.95 | 29.3% / 1.19 / -31% | 1.16 / 1.17 | 5.2 |
| NSE 500 | Stage-2 | 14.9% / 0.49 / -36% | 0.21 / 0.90 / 0.44 | 16.7% / 0.59 / -32% | 0.88 / 1.07 | 6.0 |
| Nifty 250 | MM base | 19.7% / 0.73 / -38% | 0.49 / 1.12 / 0.65 | 26.2% / 1.03 / -30% | 1.09 / 1.11 | 7.0 |
| Nifty 250 | Dip feed | 18.0% / 0.70 / -33% | 0.56 / 1.14 / 0.46 | 20.7% / 0.84 / -24% | 0.97 / 1.05 | 4.5 |
| Nifty 250 | Stage-2 | 15.3% / 0.53 / -36% | 0.23 / 0.71 / 0.68 | 20.5% / 0.79 / -28% | 0.99 / 1.14 | 4.7 |

1. **The dip feed on NSE 500 is the one cell at the MM base or above**:
   OOS 22.2% / 0.85 / −34% against 21.7% / 0.78 / −34%, with the better
   Wright window (29.3% / 1.19 vs 21.1% / 0.74) and the better down-capture
   (1.17 vs 1.37) at a slightly higher up-capture (1.16). It gets there on
   a third of the trades. Its weakness is the same as MM's, 2016-19 (0.25),
   and it does not pass G2 (0.9) any more than MM does.
2. On Nifty 250 the dip feed is a wash against MM (0.70 vs 0.73) with a
   shallower drawdown; 2023-26 is weak (0.46) and the 2025-26 entry cohorts
   are the worst in the sample (33% and 6% win rates).
3. **Stage-2 is below the MM base on both universes in every window**, on
   Sharpe, CAGR and drawdown alike. Its published case rested on a
   drawdown edge that does not exist on the honest store, and its up-capture
   (0.88-0.99) is the lowest here. Nothing in it argues for a slot.
4. Neither strategy's IS/OOS split is clean for the strategy: S2-v2's
   variant and the dip arm were both selected on their sources' 2017-2026
   data. The 2016-26 column here is the same period their rules were
   chosen on, run on a different universe; it is not a fresh test.
5. Trade shape, for a calls product: the dip feed is a positive-skew feed —
   45-47% winners, average winner +37% to +43% against −12% to −14%
   losers, one call in ten above +50%, median call slightly negative, the
   trail taking 50-70% of exits. Stage-2 is a hit-rate book — 51-52%
   winners, +21% / −13%, expectancy +4% to +6%, no stop. The by-year tables
   show both feeds' expectancy going negative in 2018-19 and 2025-26 on
   NSE 500.

## What could not be ruled out

- The master store's membership effective dates and rename stitching are
  taken as given from `market_data_spine`; a wrong date there is a
  look-ahead this task would not see.
- Delist at LTP is optimistic: a delisted holding is sold at its last
  print, which a real book might not get. Both strategies inherit it;
  the dip feed can hold a flat name for up to ~6 months before its rank
  decays through 0.35.
- Prices are Kite back-adjusted (today's factors applied to history).
  Every signal here is a ratio or a percentile, so levels do not matter,
  but the adjustment itself is applied with hindsight.
- The MidSmall 400 series is synthetic (`om25_rebuild`), as in the MM
  report.
