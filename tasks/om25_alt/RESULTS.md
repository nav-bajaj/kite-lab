# OM25 Alternatives — Results

**Status (2026-05-21): CLOSED.** No production change recommended. The six
candidate portfolios tested all failed the bar of "genuinely differentiated
from L6 / OM25 AND meaningful returns." Production portfolios are working
well in their current form.

This document captures what was tested, what the data showed, and why the
search closed. See `om_25_alt.md` for the original brainstorm that opened
this branch.

---

## The question

Production has OM25 (Quality Momentum, Nifty 250) and L6 (Core Momentum,
NSE 500). They overlap behaviourally — both load on momentum-adjacent
factors. The exploration was: **can we build a new portfolio that has
both a different return profile and a different drawdown profile from
L6 / OM25, while still delivering meaningful returns** (the audience is
DIY investors chasing returns, not capital-preservation investors)?

Differentiation bar:
- Daily-return correlation with L6 below ~0.7 (production is 0.18–0.29 between L6 and OM25)
- Holdings overlap below ~25% (production: 29% between L6 and OM25 N250)
- A meaningfully different drawdown shape

Return bar: "meaningful" implies OOS Sharpe and CAGR competitive with L6 / OM25
after taxes and biweekly churn — roughly 1.5+ Sharpe and 30%+ CAGR.

---

## Candidates tested

All evaluated on the same 4 windows inherited from `oos_retune_2026`:

| Window | Period | Notes |
|---|---|---|
| IS    | 2009-09 → 2016-12 | 7y in-sample |
| OOS-A | 2017-01 → 2019-12 | IL&FS sideways/bear |
| OOS-B | 2020-01 → 2022-12 | COVID + 2021 rally + 2022 rotation |
| OOS-C | 2023-01 → 2026-05 | Small/mid mania + 2025 correction |

Engine config standard for all: top-25, biweekly Friday signals, 100%
exposure, 20% from-peak stop on, exit-buffer 20, max 7.5% per position,
20 bps slippage. Differences are in the score function and universe.

| # | Candidate | What it tries |
|---|---|---|
| 1 | **ROM25** | Relative Omega — Omega ratio computed on excess returns over NIFTY 100 (proxy for Nifty 500). Tests "consistent market-outperformance" as a factor. |
| 2 | **LV25** | Pure low-volatility — percentile-rank of −252-day realised volatility. Classic textbook low-vol factor. |
| 3 | **MV25** | Moderate-vol momentum — drop top 30% by total vol, then rank by 126-day raw return. |
| 4 | **MV25d** | Same as MV25 but uses *downside* semi-deviation (`sqrt(mean(min(r,0)^2))`) for the vol filter. |
| 5 | **OM25d_NSE500** | OM25's UC/CR score applied to a downside-vol-filtered NSE 500 universe. |
| 6 | **OM25d_Nifty250** | OM25's UC/CR score applied to a downside-vol-filtered Nifty 250 universe — closest to a production-swap candidate. |

---

## Full OOS-aggregate (equal-weighted across A/B/C)

| Variant | OOS Sharpe | OOS CAGR | OOS MaxDD avg | Overlap with L6 | Daily ret corr with L6 | Verdict |
|---|---|---|---|---|---|---|
| **OM25_Nifty250** (production) | **1.69** | 40.9% | -25.7% | 29.3% | ~0.88 | Production baseline |
| **OM25_NSE500** | **1.87** | 47.1% | -30.9% | 44.2% | ~0.92 | Same score, broader universe |
| **L6_NSE500** (production) | 1.59 | 45.2% | -32.4% | 100% | 1.00 | Momentum baseline |
| ROM25_NSE500 | 1.50 | 38.6% | -32.6% | **45.9%** | **0.92** | Momentum in disguise |
| LV25_NSE500 | 0.83 | 14.6% | -19.5% | **3.6%** | **0.66** | Genuinely different but returns too low |
| MV25_NSE500 | 1.09 | 27.0% | -25.9% | 38.3% | 0.84 | Worst-of-both — defensive cost without differentiation |
| MV25d_NSE500 | 1.44 | 35.9% | -26.8% | 52.8% | 0.87 | Best new candidate, but 53% overlap with L6 — not different enough |
| OM25d_NSE500 | 1.47 | 34.5% | -26.5% | 31.1% | ~0.83 | Filter destroys OM25's value |
| OM25d_Nifty250 | 1.30 | 29.7% | -25.2% | 19.4% | ~0.79 | -0.39 Sharpe and -11pp CAGR vs production OM25 |

## Recent-era window (2021-01-01 → 2026-05-08, ~5.3 years)

Stitched OOS-B (clipped to 2021-01-01+) + OOS-C. The "live deployment era".

| Variant | CAGR | Sharpe | MaxDD | Calmar | Total return |
|---|---|---|---|---|---|
| **OM25_NSE500** | **60.17%** | **2.13** | -32.1% | 1.88 | 1141% (11.4×) |
| OM25d_Nifty250 | 40.72% | 1.86 | **-25.7%** | 1.59 | 521% |
| ROM25_NSE500 | 46.87% | 1.79 | -31.1% | 1.51 | 681% |
| OM25_Nifty250 (production) | 45.60% | 1.77 | -28.2% | 1.62 | 645% |
| OM25d_NSE500 | 42.78% | 1.76 | **-24.0%** | **1.78** | 571% |
| MV25d_NSE500 | 44.68% | 1.71 | -33.1% | 1.35 | 621% |
| L6_NSE500 (production) | 50.38% | 1.68 | -31.4% | 1.61 | 786% |
| MV25_NSE500 | 34.78% | 1.44 | -28.9% | 1.20 | 393% |
| LV25_NSE500 | 15.72% | 0.82 | -23.9% | 0.66 | 118% |

Notable: in the recent-era window only (excluding OOS-A IL&FS), the downside-vol filter
on OM25 actually *helps* on Nifty 250 (Sharpe 1.86 vs 1.77, MaxDD -25.7% vs -28.2%).
Over full OOS A+B+C, it hurts. So the conclusion is regime-dependent.

---

## Why the search closed

### Pattern across candidates

Every defensive tilt we tested collapsed onto one of two attractors:

1. **Momentum in disguise** (ROM25, MV25, MV25d) — high correlation and overlap with L6 (0.84–0.92, 38–53% overlap). Return profile similar to L6, occasionally slightly worse. Doesn't justify a separate product.

2. **Too defensive** (LV25, MV25 partially) — clear differentiation (3.6% overlap, 0.66 correlation) but OOS CAGR is 15–27% with Sharpe 0.83–1.09. Wrong product for the audience.

The middle ground we hoped for — "lower drawdown, meaningful returns, materially decorrelated" — kept failing because:

- **OM25's UC/CR already does the defensive work**. Layering downside-vol filter on top is redundant and net negative (OM25d destroys 0.39 Sharpe and 11pp CAGR vs production).
- **Pre-filtering universe by vol removes momentum winners**. Vol *is* upside in equity momentum; filtering it removes the alpha along with the noise (MV25's failure mode).
- **The downside-vol filter helps raw momentum** (+0.35 OOS Sharpe vs MV25), but the resulting strategy converges toward L6 — 53% holdings overlap, 0.87 daily correlation. Not a new product.

### Where the data led us back to production

| Strategy | OOS Sharpe | 2021+ Sharpe | Notes |
|---|---|---|---|
| **OM25_Nifty250 (production)** | **1.69** | 1.77 | Strong across all windows |
| OM25_NSE500 | 1.87 | 2.13 | Better but mostly the universe expansion (already known) |
| L6 (production) | 1.59 | 1.68 | Solid; ~5pp behind OM25 family in the recent era |
| best new candidate (MV25d) | 1.44 | 1.71 | Trails OM25_Nifty250 across both views |

The production lineup is already strong. The recent-era data shows OM25 family beating L6 on Sharpe, which is itself a useful diagnostic finding — not a reason to launch a new product.

### Specific candidates closed

- **ROM25** — rejected. Excess-return Omega is momentum-flavoured. Ranks essentially the same stocks (46% overlap with L6, 0.92 correlation). Lower OOS Sharpe than baseline.
- **LV25** — rejected for this product. Genuinely orthogonal (3.6% overlap) but 14.6% OOS CAGR is wrong for DIY-aggressive subscribers.
- **MV25 (total-vol filter + momentum)** — rejected. Worst-of-both: 27% CAGR, 1.09 Sharpe, no drawdown protection.
- **MV25d (downside-vol filter + momentum)** — rejected as a *new product*. 36% CAGR / 1.44 OOS Sharpe is decent but 53% overlap with L6 makes it a near-clone, not a new offering. (Possible "L6 v3" with half the turnover, but that's a future production upgrade, not new portfolio.)
- **OM25d on both universes** — rejected. The filter destroys OM25's own defensive logic. Net -0.39 Sharpe and -11pp CAGR on Nifty 250 (full OOS).

---

## What we learned that wasn't a "no"

1. **OM25's CR factor is doing more work than a separate filter could.** Across all variants that tried to add defensive characteristics on top of OM25, the result was worse than OM25 alone. The score itself contains the defensive signal.

2. **L6 (NSE 500 momentum) trails OM25 on Sharpe in the recent era.** 1.68 vs 1.77 OOS post-2021. L6's lack of any defensive component is a real cost in the current correction-heavy regime. Worth keeping an eye on, possibly an *internal* candidate for adding a regime overlay (the breadth-atlas work is exactly this).

3. **The Indian equity universe doesn't have an obvious "defensive momentum" sweet spot.** Vol is highly correlated with momentum returns; pre-filtering one removes the other. This is a structural property of the market, not a flaw in any candidate's design.

4. **OM25_NSE500 (OM25 score on the broader universe) is the highest-Sharpe configuration we found** — 1.87 OOS, 2.13 in recent era. But it overlaps 44% with L6 and is mostly a universe-expansion effect. Could be deployed as an upgrade to OM25 (Nifty 250 → NSE 500) rather than a new portfolio. Out of scope for this exploration.

---

## File index

```
tasks/om25_alt/
  om_25_alt.md                  # original brainstorm (the menu)
  RESULTS.md                    # this file
  rom25_experiment.py           # ROM25 sweep + diagnostics
  lv25_experiment.py            # LV25 sweep + diagnostics
  mv25_experiment.py            # MV25 + MV25d (single script, --vol-measure flag)
  om25d_experiment.py           # OM25d on both universes + diagnostics
  analyze_2021plus.py           # stitches OOS-B + OOS-C for the recent-era view
```

Run outputs (equity CSVs, summary CSVs, overlap, correlation matrices) are
stored under `tasks/om25_alt/runs/<ts>/` and gitignored (regenerable, ~16 MB).

## Reproducibility

```
python tasks/om25_alt/rom25_experiment.py
python tasks/om25_alt/lv25_experiment.py
python tasks/om25_alt/mv25_experiment.py                       # MV25 total-vol
python tasks/om25_alt/mv25_experiment.py --vol-measure downside  # MV25d
python tasks/om25_alt/om25d_experiment.py
python tasks/om25_alt/analyze_2021plus.py                      # recent-era summary
```

Each experiment script saves a timestamped directory under
`tasks/om25_alt/runs/` with `summary.csv`, `config.json`, an `overlap.csv`
diagnostics file, a `daily_corr.csv`, and one equity CSV per
(variant × window). End-to-end runtime is ~15–25 min per sweep.

---

## Decision

**No production change.** The existing 4-portfolio lineup (OM25 v3,
TL25 v3, L6 v2, COMBO Defensive) is performing well and the search for a
clearly-differentiated additional offering yielded no viable candidate.

If we revisit, the most productive angles based on this evidence:

1. **A specific diagnostic on COMBO** (it's surfacing only 5 positions when 24 are expected — likely a configuration or signal issue, not a strategy redesign).
2. **OM25 universe expansion** (Nifty 250 → NSE 500) as a production upgrade rather than a new portfolio — the data clearly supports this.
3. **Applying the breadth 3-state work to L6 as an exposure overlay** — L6's lack of regime gate is the clearest gap, and the breadth atlas already validated that a deep-state override has value on the OM25 substrate.

None of those are open work as of this commit.
