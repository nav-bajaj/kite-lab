# OM25 v3 US retune — RESULTS

**Date:** 2026-05-14 to 2026-05-15
**Branch:** `us-data`
**Author:** nav + Claude
**Status:** **Tuning rejected.** Locked Indian OM25 v3 (unchanged) outperforms US-retuned config on OOS Sharpe and CAGR. The US retune produced a defense-tilted CR-only variant that drops 11pp of CAGR for 10pp of DD shallowness — a worse risk-adjusted strategy.

## Why this work

OM25 v3 on US data (locked Indian params, no tuning, from `tasks/us_equities_2017/RESULTS.md`) showed a Sharpe drop vs Indian OOS:

| | India OOS 2017-26 | US OOS 2017-26 |
|---|---:|---:|
| CAGR | 44.78% | 34.40% |
| Sharpe | 1.86 | 1.26 |
| MaxDD | −36.60% | −41.15% |

Hypothesis: the UC/CR bull-regime weights (50/50) and the NIFTY-100-based regime panel don't transfer cleanly to US. Worth a structured retune to see if US-specific parameters lift performance.

## Methodology

Mirrored `tasks/oos_retune_2026/PLAN.md` methodology:

| Window | Period | Length |
|---|---|---:|
| IS | 2009-09-01 → 2016-12-31 | 7.3y |
| OOS_A | 2017-01-01 → 2019-12-31 | 3y |
| OOS_B | 2020-01-01 → 2022-12-31 | 3y |
| OOS_C | 2023-01-01 → 2026-05-13 | 3.4y |
| OOS_full | 2017-01-01 → 2026-05-13 | 9.4y |

**Universe:** SP500 ∪ NDX (516 symbols).
**Engine:** `_clean_engine.run_strategy()` with `om25_v3.make_om25_tilt_score` (or its closure variant supporting skip).
**Regime panel:** SPY 100-DMA, 3-day confirm (replaces NIFTY 100 100-DMA).
**Selection criterion:** highest IS Sharpe.
**Pass criteria:** IS Sharpe ≥ 1.0, OOS-full Sharpe ≥ 1.0, sub-window Sharpe ≥ 0.7, OOS-full MaxDD ≥ −45%.

## Stages

| Stage | Lever | Configs | Winner |
|---:|---|---:|---|
| 1 | Score variants (w_uc / w_cr × return_filter × min_obs) | 20 | **w_uc=0.0, w_cr=1.0** (pure CR) on top 4 |
| 2 | Execution (lookback × top_n × buf × cadence × ATR-stop) around top-3 stage-1 | 37 | **monthly, L126, top_n=25, buf=15** |
| 3 | Regime tilt overlay on top-1 per cadence (MA × confirm × bear weights) | 72 | **No improvement** — base wins |
| 4 | Skip_days on per-cadence Stage-3 winners | 8 | **skip=0** — skip hurts CR signal |

Total: ~137 backtests, ~45 min wall.

## Stage-by-stage findings

**Stage 1 — score weights:** Top 4 configs all had **w_uc=0.0, w_cr=1.0** (pure capture-ratio). Indian production ships 50/50 UC/CR. On US data, upside-capture is dead weight; only capture-ratio (UC/DC) carries cross-sectional signal. Probable cause: US large-caps have tighter UC distribution than NSE 250, so UC doesn't differentiate; CR (which combines up/down asymmetry) is the only meaningful ranking dimension.

**Stage 2 — execution:** Monthly cadence beats biweekly by 0.10 Sharpe. Lookback 126 beats 252 on monthly cadence (CAGR same, DD better, fewer trades). Top_n=25 / buf=15 wins on the top-3 stage-1 baselines.

**Stage 3 — regime tilt:** Top 5 by IS Sharpe have **identical** CAGR / DD because the bear weights `(0, 1.0)` equalled the bull weights — the regime panel was toggling between two identical scoring functions, a structural no-op. Configs where bear weights actually differed (0.25/0.75, 0.5/0.5) scored *worse* than base.

**Stage 4 — skip_days:** Skip {0, 5, 21, 42} on both per-cadence Stage-3 winners. **Skip hurts monotonically**. Best: skip=0 (monthly Sharpe 1.31), worst: skip=42 (monthly Sharpe 1.12). The Jegadeesh-Titman 12-1 momentum trick works for momentum signals (which mean-revert short-term) but doesn't help a 252-day capture-ratio quality signal.

## Final US-tuned config

```
lookback=126  w_uc=0.0  w_cr=1.0  return_filter=True  min_obs=110
top_n=25  exit_buffer=15  cadence=monthly  skip_days=0
atr_mult=0  atr_min_floor=0  regime_panel=None
IS Sharpe=1.31
```

## OOS validation

Multi-window evaluation of the tuned winner re-run over full 2009→today:

| Window | Period | CAGR | Sharpe | MaxDD |
|---|---|---:|---:|---:|
| IS | 2009-11 → 2016-12 | 21.24% | 1.31 | −18.80% |
| OOS_A | 2017-2019 | 16.15% | 1.22 | −19.77% |
| OOS_B | 2020-2022 | 23.92% | 0.98 | −30.91% |
| OOS_C | 2023-2026 | 30.14% | 1.57 | −19.89% |
| **OOS_full** | 2017-2026 | **23.27%** | **1.19** | **−30.91%** |

**Pass criteria: PASS ✓** on all metrics. Strict pass; OOS_B Sharpe of 0.98 nearly fails the 0.7 floor (it passes the floor but is well below the 1.0 OOS-full target on this sub-window).

## Honest comparison vs locked Indian v3 on US

This is the key result. Locked Indian v3 ran on US data (zero tuning) is in `tasks/us_equities_2017/RESULTS.md`:

| Metric | US-tuned winner | Locked v3 on US | Δ |
|---|---:|---:|---:|
| **OOS-full CAGR** | 23.27% | **34.40%** | **−11.13pp** |
| **OOS-full Sharpe** | 1.19 | **1.26** | **−0.07** |
| **OOS-full Calmar** | 0.75 | **0.84** | −0.09 |
| OOS-full MaxDD | **−30.91%** | −41.15% | +10.24pp shallower |

**The US retune produces a worse strategy on every risk-adjusted metric.** The 10pp DD reduction is real but pays −11pp CAGR and −0.07 Sharpe.

The retune effectively replaced OM25's *quality-tilted momentum* identity (UC/CR composite + regime tilt) with a *pure defensive quality* signal (CR-only, no regime). It lost the upside engine while gaining only defense.

## Why the retune found a defensive variant

IS-Sharpe-max selection has a known bias toward low-vol configs. On US data 2009-2016:

1. **UC normalisation is weak** — US large-caps have tighter upside-capture dispersion than NSE 250, so the UC component of the score adds little ranking signal. Dropping it (w_uc=0) cleans up the score without hurting much.
2. **CR alone is structurally defensive** — capture-ratio rewards stocks with high upside-to-downside asymmetry. These tend to be low-beta, lower-vol names (insurers, healthcare, staples).
3. **IS Sharpe rewards low-vol** — by definition. A low-vol defensive portfolio with modest 20% CAGR can produce Sharpe 1.31 if the vol is low enough. The tuner picked exactly that.
4. **Regime tilt added nothing** because the CR signal was already defense-tilted by construction. Bear-regime bear-only weights produced an identical portfolio to bull-regime bull-only weights (which is what `w_uc=0, w_cr=1.0` means in both regimes).

## Recommendation

**Keep locked Indian OM25 v3 (`om25_v3.LOCKED`) for any US deployment.** Do not US-retune.

Rationale:
- Locked v3 wins on OOS Sharpe (+0.07), OOS CAGR (+11pp), OOS Calmar (+0.09).
- Locked v3's deeper DD (−41% vs −31%) is real, but the −11pp CAGR cost dominates. If lower DD is the goal, run COMBO Defensive instead (already achieves −28% DD with 38% CAGR on US 2020-26).
- The retune is structurally a different strategy — defensive quality, not regime-tilted momentum. If we want a defensive US strategy, COMBO Defensive is a better fit and is already documented.

## Linkage to the L6 retune

The L6 US retune (`tasks/l6_us_tune_2026/RESULTS.md`) reached the same verdict by the same mechanism: IS Sharpe gain (+0.14) flipped to OOS Sharpe loss (−0.16). Same overfitting signature.

Both retunes confirm the structural conclusion: **the locked Indian production configs transfer well to US, and IS-Sharpe-max retuning on either strategy makes them worse out-of-sample.** This is consistent with the prior walk-forward study on Indian data (CLAUDE.md), which found "IS Sharpe ranking carries little predictive signal at 3y windows."

## Files

- `tasks/om25_us_tune_2026/PLAN.md` — methodology + sweep design
- `tasks/om25_us_tune_2026/_om25_us_retune.py` — staged sweep harness (Stages 1-4, regime tilt + skip_days extensions)
- `experiments/oos_retune/<ts>_om25_us/stage{1,2,3,4}.csv` — per-stage results (gitignored)

## Reproducibility

```bash
# Full sweep (Stages 1-3) — ~45 min
python tasks/om25_us_tune_2026/_om25_us_retune.py
# Stage 4 skip_days sweep, resuming from prior dir
python tasks/om25_us_tune_2026/_om25_us_retune.py \
  --resume-dir experiments/oos_retune/<prior_ts>_om25_us \
  --stop-after-stage 4
```
