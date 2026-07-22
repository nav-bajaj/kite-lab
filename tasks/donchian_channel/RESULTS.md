# Donchian channel exploration — RESULTS

Ran 2026-07-22 on branch `donchian_research`. Windows and acceptance bars
pre-registered in PLAN.md / TASKS.md before any run; grid fixed at
N in {10, 20, 55, 252}; no post-hoc parameter shopping.

## Verdict summary

| Hypothesis | Verdict |
|---|---|
| H2 Donchian trailing exits on L6/OM25 | **Rejected** — IS gains do not survive OOS; existing exits already do the work |
| H1 52-week-high nearness ranking (George-Hwang) | **Rejected** — differentiated but far below the return bar; blend dominated by pure L6 |
| H3 Donchian breadth indicator | **Mostly redundant** — 252d family duplicates existing breadth; 55d family is the only semi-novel slice |
| H4 momentum-filtered breakout calls | **Filter helps modestly, product fails the validity gate** — do not publish forward-return claims; viable only as an explicitly trend-following content format |

**Decision: no production change. No new portfolio. No subscriber-facing
forward-return claims from Donchian signals.** The one optional follow-up
(founder call): a descriptive "breakout breadth" tile using
`net_channel_55`, and/or an H4-style call list published as an honest
trend-following journal (43% win rate, fat right tail) rather than as
validated recommendations — see H4 below.

---

## H2 — Donchian exit overlay (rejected)

Grid: L6 x {base, +don10, +don20, +don55}, OM25-shaped x {base 20% stop,
don10/20/55 replacing the stop, don20+stop}. 36 runs.
Run dir: `runs/h2_20260722_185006/` (regenerable).

- **IS looked good, OOS said no.** On OM25, IS Calmar improved from 1.00
  (base) to 1.12 (don20-repl) and 1.07 (don55-repl). The IS pick
  (don20-repl) then lost to base in OOS-B (Calmar 1.50 vs 1.70) and OOS-C
  (1.78 vs 1.99), passing only OOS-A (1.02 vs 1.01). Fails the
  pre-registered 3-of-3 OOS consistency bar.
- **On L6 the overlay is harmful or inert.** don10/don20 cut OOS-A CAGR by
  3-5pp with deeper drawdowns (rank exits fire first and better); don55
  triggers only 19-44 times per window — a no-op.
- **Mechanism:** exit-reason attribution shows Donchian exits mostly
  *replace* rank/stop exits rather than adding protection, while raising
  annual turnover 10-60%.

## H1 — 52-week-high nearness ranking (rejected)

Variants: GH25 (close / 252d high, top-25, production-shaped execution),
GH+L6 50/50 rank blend; comparators L6, OM25. 16 runs.
Run dir: `runs/h1_20260722_185120/`.

- **Differentiation bars: passed.** Top-25 overlap vs L6 = 24.3% (< 25%),
  daily-return corr 0.70-0.81 (borderline vs the < 0.7 bar).
- **Return bar: failed by a wide margin.** GH25 OOS CAGR 11.8-17.1%,
  Sharpe 0.42-0.65 (bar: >= 30% / >= 1.5). Worst in OOS-C (11.8%).
- **Blend dominated.** GH+L6 blend is below pure L6 in every window
  (OOS-A 15.5% vs 36.1%; OOS-B 46.4% vs 65.2%; OOS-C 21.5% vs 36.8%) —
  the GH leg dilutes momentum instead of complementing it.
- **The one confirmed literature claim: crash mitigation.** GH25 drew down
  less in both crash windows (COVID: -33.1% vs L6 -38.0%; 2025 correction:
  -18.7% vs -25.4%) — directionally consistent with FAJ 2023 — but the
  return give-up is unacceptable. The useful fragment of nearness-to-high
  already lives in TL25 v3's `(close / 126d high)^2` drawdown-control term.

## H3 — Donchian breadth (mostly redundant; descriptive only)

15 daily series (pct above prior N-day high / fresh crosses / below N-day
low / net / median channel position, N in {20, 55, 252}), 2010-06..2026-05,
written to `donchian_breadth_daily.csv` (committed). Boundary gate passed:
replica of the production `net_new_highs_pct` correlates 0.998 with
`data/breadth/breadth_daily.csv`.

- `net_channel_252` vs production `net_new_highs_pct`: **rho = 0.95** —
  redundant. `med_chanpos_252` vs `pct_above_200dma`: **rho = 0.97** —
  redundant.
- The 55-day family is the only semi-novel slice: `net_channel_55` max
  rho 0.84 (vs net_new_highs_pct), `pct_fresh_high_55` max rho 0.78 (vs
  pct_at_52w_high), `med_chanpos_55` max rho 0.77. Cross-N correlations
  0.75-0.92 — the three horizons are variations on one theme.
- Character: net-channel series mean-revert fast (AR1 half-life 1-3 days;
  spiky), channel-position medians are slow regime gauges (half-life 10,
  27, 120 days for N=20/55/252). Extremes catalog is sane: bottoms =
  2020-03 COVID days, 2011-12, 2026-03; tops = 2014-05 (Modi election),
  2023-07-31.
- **No forward-return claims tested or made** (atlas discipline). If a
  consumer appears (e.g. an insights tile), `net_channel_55` is the
  candidate and must go through `pattern_validity_study.py` for any claim.

## H4 — Momentum-filtered Donchian breakout calls (founder idea)

Simulation 2010-06..2026-05: fresh cross above prior 55-day high (also
20/10 pairing), top-quartile L6-score filter vs unfiltered control, max 25
active calls prioritized by momentum rank, next-day OHLC/4 execution,
20bps each way, P&L net of slippage. Run dir: `runs/h4_20260722_185609/`.

Headline arm (filt 55/20, capped at 25):

- **1,585 closed calls (~99/year, ~2/week), median hold 64 days.**
- **Win rate 43.7%, mean P&L +6.84%, median -2.06%** — classic
  trend-following shape: most calls lose a few percent, p95 = +56.7%.
- Portfolio-equivalent (25 equal slots): **CAGR 26.9%, Sharpe 1.33,
  MaxDD -27.1%** — well below every production portfolio.
- Good years: 2014 (+22.9% mean), 2017, 2020, 2023 (+17.1%). Bad: 2018
  (-2.7%), 2015, 2011, and notably **2025 (-2.5%) and 2026 YTD (-5.6%)** —
  the product would have looked broken for the last 18 months.

**Founder question — does the top-quartile momentum filter beat running it
on all of NSE 500?** Yes, but modestly, and the cap hides it:

- Uncapped (clean comparison): filtered mean +7.94% / win rate 44.0%
  (4,714 calls) vs unfiltered +6.96% / 42.8% (9,215 calls). The filter
  adds ~1pp expectancy and ~1.2pp win rate, and halves the call volume.
- Capped: the arms converge (6.84 vs 7.18 mean) because the 25-slot list
  is full 71-79% of days and free slots are filled by momentum rank — the
  cap + priority is itself a momentum filter. The capacity constraint, not
  the quartile screen, does most of the selection: 10,380 filtered
  breakout events (26,674 unfiltered) were skipped for capacity over the
  16 years, ~6.5x the number of calls actually issued.

**Validity gate (house 6-check protocol): FAILS.**

- 20d excess vs same-date NSE-500 baseline: **+0.49pp** (< +1.0pp bar).
- 60d excess +1.27pp but halves are inconsistent (+2.45 first half,
  +0.09 second half) — the edge has decayed within the sample.
- **Direction lift is negative at every horizon (-7 to -12pp)**: a
  breakout call is *less* likely to be up than the average NSE-500 stock
  over the same dates; the mean is carried entirely by the right tail.
  Per `VALIDITY_PROTOCOL.md` this is the "not surfaced" tier.

So: no "these calls historically returned X%" copy is publishable. The
honest framing — "trend-following entries: most calls stop out small, the
tail pays" — is a different content class the platform hasn't used, would
require exceptional care in presentation, and its recent-era stats
(2024-2026) are poor. Recommendation: do not build as a recommendation
product; if the format is still attractive, revisit as an educational /
transparency journal with the full loss distribution shown.

## What we learned that wasn't a no

- The engine's `donchian_low_panel` hook works as documented; prior-window
  (shift-1) bands are mandatory or the exit can never fire (Phase 1 gate3b
  proves an inclusive window produces zero breaches).
- The breadth boundary replica (0.998) validates that our raw-CSV OHLC
  loader agrees with the production close-panel pipeline — reusable for
  any future high/low research.
- GH crash mitigation is real in NSE 500, just not worth the carry. If we
  ever need a defensive tilt lever, nearness-to-high is a confirmed
  ingredient (TL25 already holds it).
- Breakout-call P&L shape (43% win, fat tail) matches the Turtle-rules
  primary source's own description — the sim is faithful to the class.

## Reproducibility

```
source .venv/bin/activate
python tasks/donchian_channel/channel_panels.py            # Phase 1 gates
python tasks/donchian_channel/h2_donchian_exit_experiment.py
python tasks/donchian_channel/h1_nearness_experiment.py
python tasks/donchian_channel/h3_breadth_profile.py
python tasks/donchian_channel/h4_breakout_calls.py
```

Outputs land in `tasks/donchian_channel/runs/<phase>_<ts>/` (gitignored,
regenerable). Inputs: `nse500_data_merged/`, `data/static/*.csv`,
`data/benchmarks/nifty100.csv`, `indices_data_historical/NIFTY_100.csv`,
`data/breadth/breadth_daily.csv`.

Caveats: current-snapshot universe (survivorship — same-date baselines
partially cancel it; disclosed per atlas precedent); no STT/taxes beyond
20bps slippage; H4 assumes fills at next-day OHLC/4 which is optimistic
for low-liquidity breakouts.

## File index

- `LITERATURE.md` — verified literature review (Turtle primary source,
  BLL 1992, STW 1999, Park-Irwin 2007, George-Hwang 2004, India evidence)
- `channel_panels.py` — OHLC panel loader + prior-window Donchian bands +
  sanity gates
- `h2_donchian_exit_experiment.py`, `h1_nearness_experiment.py`,
  `h3_breadth_profile.py`, `h4_breakout_calls.py` — phase scripts
- `donchian_breadth_daily.csv` — H3 cached panel (committed)
- `runs/` — gitignored experiment outputs
