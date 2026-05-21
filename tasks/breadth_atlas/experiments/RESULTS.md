# Breadth-Regime Experiments — Results

**Status (2026-05-21):** exploratory. No production change recommended yet.

This document summarises the 3-state breadth-regime experiments built on top of
the breadth atlas (see `../REPORT.md`). The headline question was: **can we
use breadth metrics to define a richer regime than the production NIFTY-100
close-vs-100dma 2-state gate, and does it improve any of the production
portfolios?**

The work spans four iterations of design, three universes, six breadth
metrics, four windows (IS + three OOS sub-windows inherited from
`oos_retune_2026`), and four portfolios (OM25, TL25, L6, COMBO).

---

## Windows (inherited from `oos_retune_2026`)

| Window | Period | Years | Character |
|---|---|---|---|
| IS    | 2009-09 → 2016-12 | 7.3 | Mixed; tune-on |
| OOS-A | 2017-01 → 2019-12 | 3.0 | Sideways / IL&FS — the bear-style sub-window |
| OOS-B | 2020-01 → 2022-12 | 3.0 | COVID crash + 2021 mega-rally + 2022 rotation |
| OOS-C | 2023-01 → 2026-05 | 3.4 | Small/mid-cap mania + 2025 correction |

All metrics are computed on the active entry window only, not on equity drift
into post-window periods (an early-iteration bug; fixed).

---

## Design space tested

### Regime architectures

| Variant | Description |
|---|---|
| 2-state (production-like) | NIFTY-100 close-vs-100dma, 3-day confirm. Bull / bear. |
| 3-state breadth | Adds a "deep value" state below atlas-p5 of the chosen breadth metric. Sticky machine: bull↔bear↔deep, no direct bull↔deep transitions. Asymmetric thresholds for hysteresis. |
| 2-state breadth | Normal / deep only. No bear de-risking. |

### Breadth metrics tested as the regime driver

All thresholds are atlas-derived (p25/p5 percentiles with a hysteresis band on
exit). No threshold optimisation on IS.

| Metric | (bear_in, bear_out, deep_in, deep_out) | Comment |
|---|---|---|
| `pct_above_200dma` | (0.40, 0.50, 0.20, 0.30) | Atlas headline metric, slow level signal |
| `avg_dist_from_200dma` | (0.00, 0.05, -0.10, -0.05) | Continuous version; more deep samples |
| `pct_above_100dma` | (0.40, 0.50, 0.20, 0.30) | Faster horizon |
| `pct_above_50dma` | (0.40, 0.50, 0.20, 0.30) | Even faster |
| `net_new_highs_pct` | (0.00, 0.03, -0.10, -0.05) | Asymmetric — independent of pct_above_200dma (ρ=0.73) |
| `mcclellan_sum` | (2.50, 2.70, 1.50, 1.80) | Slow flow indicator |

### Score-tilt variants tested on OM25

| State weights | Bull | Bear | Deep | Notes |
|---|---|---|---|---|
| **Anchor (winner-class)** | UC 0.5 / CR 0.5 | UC 0 / CR 1 | UC 1 / CR 0 | Production bull weights + defensive bear + aggressive deep |
| Pure-UC bull | UC 1 / CR 0 | UC 0 / CR 1 | UC 1 / CR 0 | Collapses bull and deep — *rejected* (lost 0.47 OOS Sharpe) |
| 2-state no-bear | UC 0.5 / CR 0.5 | — | UC 1 / CR 0 | Worked on NSE 500, hurt Nifty 250 |

### Mechanical levers (anchor design — all states)

- **Exposure:** 100% always (no de-risking — explicit user constraint)
- **Drawdown stop:** 20% from-peak weekly check, on in every state
- **Other:** top-25, exit-buffer 20, biweekly Friday signals, 20bps slippage

A misguided earlier iteration (deep_drawdown_stop=0.0) was discovered to
accidentally exit on any drop below peak; the fix is `floor=1.0` or simply
matching production's 0.20 in every state, which is what we use.

---

## Applicability to OM25 — the main story

OM25 v3 (production) uses UC (upside capture) and CR (capture ratio = UC/DC)
percentile-ranks. Its production score is 0.5×UC + 0.5×CR in bull and pure
CR in bear, with a NIFTY-100 close-vs-100dma 2-state gate. The breadth
regime swaps this NIFTY-100 gate with the 3-state breadth machine and adds a
deep-state UC-only score flip.

### OM25 result matrix — OOS-aggregate Sharpe (equal-weighted across A/B/C)

| Universe | Baseline (production) | 3-state breadth | 2-state breadth (no bear) |
|---|---|---|---|
| **Nifty 250** | **1.75** | 1.76 | 1.59 |
| **NSE 500** | 1.87 | **2.19** | 1.97 |

### Per-window detail (best variant: `avg_dist_from_200dma`)

**Nifty 250 — production universe.** Net effect is essentially neutral.

| Window | Baseline | 3-state breadth | Δ Sharpe |
|---|---|---|---|
| IS | 27.81 / 1.37 / -26.4% | 28.81 / 1.36 / -26.3% | -0.01 |
| OOS-A | 23.74 / 1.19 / -21.0% | **27.67 / 1.40 / -15.5%** | **+0.21** |
| OOS-B | 55.04 / 2.12 / -31.3% | 59.32 / 2.26 / -31.7% | +0.14 |
| OOS-C | 44.10 / 1.75 / -24.8% | 41.79 / 1.61 / -24.7% | -0.14 |

**NSE 500.** Genuine cross-window improvement — wins all three OOS.

| Window | Baseline | 3-state breadth | Δ Sharpe |
|---|---|---|---|
| IS | 27.63 / 1.23 / -28.4% | 26.97 / 1.13 / -28.1% | -0.10 |
| OOS-A | 29.72 / 1.32 / -33.9% | **43.26 / 2.08 / -19.7%** | **+0.76** |
| OOS-B | 67.00 / 2.56 / -34.0% | **74.24 / 2.73 / -34.8%** | +0.17 |
| OOS-C | 44.50 / 1.72 / -24.7% | 47.58 / 1.75 / -28.8% | +0.03 |

### What's universe vs what's regime

Decomposing the NSE 500 + 3-state OOS Sharpe of 2.19 against components:

| | OOS Sharpe | OOS CAGR | OOS MaxDD |
|---|---|---|---|
| NSE 500 + 3-state breadth | **2.19** | 55.4% | -34.8% |
| Nifty 250 + 3-state breadth | 1.76 | 42.0% | -31.7% |
| Nifty 250 + baseline (production) | 1.75 | 41.6% | -31.3% |

Conclusion: most of the OOS gain (≈+0.44 Sharpe) is the **NSE 500 universe
expansion**, not the regime change. On the production Nifty 250 universe, the
breadth regime gives essentially a neutral net result. Its main practical
contribution there is **OOS-A drawdown reduction**: -5.5pp MaxDD, Calmar
1.78 vs 1.13 — a 57% Calmar improvement in the worst-Sharpe OOS window.

### Year-by-year — Nifty 250 + 3-state breadth

(Same universe as production. Demonstrates *what the regime does*, isolated
from the universe expansion.)

| Year | Window | 3-state ret% | Baseline ret% | Spread | Days in deep |
|---|---|---|---|---|---|
| 2010 | IS    | 32.6 | 30.9 |  +1.8 |  0 |
| 2011 | IS    | -9.6 | -13.9 |  +4.4 | 81 |
| 2012 | IS    | 53.5 | 48.9 |  +4.6 | 24 |
| 2013 | IS    | 21.3 | 21.9 |  -0.6 | 73 |
| 2014 | IS    | 74.1 | 77.8 |  -3.7 |  0 |
| 2015 | IS    | 20.0 | 25.1 |  -5.1 |  0 |
| 2016 | IS    | 14.2 | 10.4 |  +3.8 | 26 |
| 2017 | OOS-A | 70.6 | 74.6 |  -4.0 |  0 |
| 2018 | OOS-A |  1.5 | -5.4 | **+7.0** | 53 |
| 2019 | OOS-A | 19.3 | 13.7 |  +5.6 | 43 |
| 2020 | OOS-B | 51.7 | 47.5 |  +4.2 | 68 |
| 2021 | OOS-B | 112.0 | 110.4 |  +1.6 |  0 |
| 2022 | OOS-B | 21.7 | 27.9 |  -6.3 | 21 |
| 2023 | OOS-C | 79.3 | 82.3 |  -3.0 |  0 |
| 2024 | OOS-C | 72.3 | 69.8 |  +2.5 |  0 |
| 2025 | OOS-C | -4.1 |  1.4 |  -5.4 | 43 |
| 2026 | OOS-C |  6.2 |  6.1 |  +0.0 | 19 |

Pattern: gains concentrate in **breadth-crash years** (2011, 2018, 2019,
2020) where the deep-state UC flip catches bouncers. Losses cluster in
**slow-grind years** without breadth crashes (2014, 2015, 2022, 2025) where
the bear-state CR tilt picks defensive names that lag the broad recovery.

---

## Winning settings

### Anchor 3-state config (the recommended starting point)

| Setting | Value |
|---|---|
| Score (bull) | UC 0.5 / CR 0.5 (production bull weights) |
| Score (bear) | UC 0.0 / CR 1.0 (defensive — pure capture ratio) |
| Score (deep) | UC 1.0 / CR 0.0 (aggressive — pure upside capture) |
| Exposure | 100% in every state |
| Drawdown stop | 20% from-peak, weekly check, on in every state |
| Universe | OM25's production Nifty 250 *or* NSE 500 (see below) |
| Breadth metric | `avg_dist_from_200dma` (most consistent across windows) |
| State machine | 3-state, sticky, no direct bull↔deep transitions |
| Confirm days | 3 |
| Thresholds | bear_in=0.00, bear_exit=0.05, deep_in=-0.10, deep_exit=-0.05 |

### Universe choice — open question

- **NSE 500** delivers higher absolute Sharpe and CAGR but is a meaningful
  deviation from production OM25 (which is locked on Nifty 250). The Sharpe
  improvement of +0.32 OOS vs baseline is genuine but ~0.44 of it comes
  from the universe change itself, not the regime mechanic.
- **Nifty 250** keeps production universe; the regime adds essentially no
  net OOS Sharpe but **does** materially cut OOS-A drawdown (-5.5pp MaxDD,
  Calmar 1.78 vs 1.13).

If the deployment goal is **risk reduction during bear-style sub-windows
without changing universe**, the Nifty 250 anchor design is worth deploying.
If the goal is **maximum risk-adjusted return** and we accept a universe
change, the NSE 500 anchor design is the winner — with the caveat that this
mostly tests "OM25 score on a broader universe" and only secondarily tests
the regime mechanic.

### What does NOT work (rejected variants)

- **Bull = pure UC** — collapses bull and deep into the same score; loses
  CR's downside discipline in normal markets. -0.47 OOS Sharpe vs anchor.
  CR is doing real work in OM25's bull state.
- **Exposure scaling** (bear=50%) — earlier exploration; user constraint
  removed it. Reduces CAGR substantially without proportional drawdown gain.
- **deep_drawdown_stop = 0.0** — bug (this means "exit on any negative
  return from peak", not "off"). To turn the stop off use `floor=1.0` (or
  any value > expected max drawdown). Current design keeps the 20% stop in
  every state anyway.

---

## Cross-portfolio transfer — brief

Tested the score-tilt 3-state design on TL25, L6, COMBO (NSE 500 + Nifty 250).
OOS-aggregate Sharpe (equal-weighted across A/B/C):

| Portfolio | Universe | Baseline | Breadth 3-state | Δ |
|---|---|---|---|---|
| TL25 | NSE 500 | 1.31 | 1.31 | +0.00 |
| TL25 | Nifty 250 | 1.24 | 1.24 | +0.01 |
| L6 | NSE 500 | 1.60 | 1.63 | +0.03 |
| L6 | Nifty 250 | 1.32 | 1.33 | +0.01 |
| **COMBO** | **NSE 500** | **1.57** | **1.70** | **+0.13** |
| COMBO | Nifty 250 | 1.57 | 1.61 | +0.04 |

**The breadth regime is OM25-shaped, not universal.** It transfers cleanly
to COMBO (which contains an OM25 component) but not to TL25 or L6.

- **TL25** has an eligibility filter (Close > 200-DMA + slope-up) that
  empties the universe during real breadth crashes. The deep-state weight
  tilt has nothing eligible to score.
- **L6** uses a single momentum/vol z-score. The vol_power tilt we tried
  doesn't bite after cross-sectional z-normalisation — picks barely change.
- **COMBO** inherits the OM25 benefit through its OM25 component; OOS-A
  Sharpe 1.57 vs 1.12 baseline on NSE 500 mirrors the OM25 standalone story.

This pattern suggests the breadth 3-state earns its keep when the underlying
score has an explicit defensive↔aggressive factor decomposition (UC↔CR).
Pure-momentum or eligibility-gated portfolios don't have the surface area.

---

## Caveats and known limits

1. **No threshold optimisation on IS.** Thresholds are fixed from atlas
   percentiles. This is by design — IS has too few deep events (~3-4) to
   fit thresholds reliably. If you want to tighten this, walk-forward
   threshold robustness is the next study.

2. **Survivorship bias.** The 250 / 500 universes are 2026-vintage. Stocks
   delisted 2010-2026 are not in the panel. Likely inflates IS performance
   modestly across all variants. Effect is symmetric across baseline and
   breadth variants, so the *relative* comparison should be reliable.

3. **The 2025 underperformance is real.** On Nifty 250 + 3-state vs
   baseline, 2025 is -5.4pp. On NSE 500 + 3-state vs baseline, 2025 is
   -11.4pp. The deep state fired (43 days) but the UC tilt didn't catch
   rebounders in the slow 2025 correction. This is the live-relevant year.

4. **Stitched continuous equity** (used for full-period numbers) rebases
   PV at each window join — so cross-window compounding is not strictly
   real. The per-window numbers are the authoritative comparison.

5. **The IS reproduction of OM25 v3** (28.59% / 1.60 / -26.5% in archived
   `oos_retune_2026`) matches almost exactly when restricted to the active
   IS entry window. Earlier-iteration "IS MaxDD -41%" was an artefact of
   the metrics windowing bug — actually COVID 2020-03-23 from held
   positions, not anything from the IS window itself.

6. **The IL&FS OOS-A win is sample-of-one.** OOS-A spans 3 years and one
   bear-style regime. The +0.21 Nifty 250 / +0.76 NSE 500 OOS-A Sharpe
   improvement is real on this data but needs walk-forward stress testing
   before deployment.

---

## What's next (not done in this iteration)

1. **Walk-forward stress test** — same procedure as `walk_forward_2026`.
   Run the anchor 3-state config through ~78 rolling 3y-IS / 1y-OOS
   slices and confirm the OOS-A-style win recurs robustly, not as
   sample-of-one IL&FS luck.

2. **OOS-A trade decomposition** — pull the trades from the NSE 500 +
   3-state run during 2018-Oct → 2018-Dec and 2019-Feb → 2019-Mar deep
   periods. What names got bought, did they actually rebound, was it
   concentrated in a sector? Distinguishes "real factor exposure" from
   "3 lucky picks".

3. **Hybrid regime** — keep production NIFTY-100 close-vs-100dma 2-state
   for bull/bear and add only the deep-state override from breadth. So
   the strategy looks like production 99% of the time and switches to
   UC-only in the ~5% of days where breadth crashes. Lowest-risk path
   to actually deploying any of this.

---

## File index

```
tasks/breadth_atlas/
  PLAN.md                          # atlas methodology
  REPORT.md                        # atlas — 14-metric profile
  experiments/
    RESULTS.md                     # this file
    om25_three_state_experiment.py # OM25 3-state sweep (the main harness)
    om25_breadth_regime_experiment.py # earlier 2-state sweep (legacy)
    portfolios_3state_breadth.py   # TL25 / L6 / COMBO cross-portfolio test
    analyze_winner.py              # per-window + year-by-year analyser
```

Each experiment script writes a timestamped run directory under
`runs_3state/<ts>/` or `portfolios_3state/<ts>/` with `summary.csv`,
`config.json`, and one equity CSV per variant. These are research
artefacts (large, regenerable) and excluded from git via `.gitignore`.

## Reproducibility

```
# Build / refresh the breadth panel (one-time, ~30s)
python scripts/build_breadth_panel.py

# OM25 3-state sweep (all 6 metrics × 2 universes × 4 windows)
python tasks/breadth_atlas/experiments/om25_three_state_experiment.py

# OM25 winner analysis (per-window + year-by-year vs production baseline)
python tasks/breadth_atlas/experiments/analyze_winner.py --winner-universe NSE500
python tasks/breadth_atlas/experiments/analyze_winner.py --winner-universe Nifty250

# Cross-portfolio: TL25 / L6 / COMBO with the 3-state breadth score-tilt
python tasks/breadth_atlas/experiments/portfolios_3state_breadth.py
```

End-to-end runtime: ~30 min on a 2024 MacBook (panel load dominates each script).
