# L6 v2 US retune — RESULTS

**Date:** 2026-05-15
**Branch:** `us-data`
**Author:** nav + Claude
**Status:** **Tuning rejected.** Locked Indian L6 (unchanged) outperforms US-tuned configs on every OOS risk-adjusted metric. Recommendation: keep locked L6 for US deployment, do not US-retune.

## Why this work

L6 v2 was the standout in the four-strategy US port (see `tasks/us_equities_2017/RESULTS.md`) — 54% CAGR / 1.64 Sharpe on US 2020-26 vs India's 59% / 1.92 in production. Worth checking if US-specific tuning lifts CAGR further, especially given US momentum literature historically favours 12-month lookback (Jegadeesh-Titman) over the 6-month lookback locked for India.

## Methodology

**Inverted IS/OOS** to avoid fitting to recent regime:

| Window | Period | Length |
|---|---|---:|
| IS | 2010-01-01 → 2017-12-31 | 8.0y |
| OOS_A | 2018-01-01 → 2019-12-31 | 2y |
| OOS_B | 2020-01-01 → 2022-12-31 | 3y |
| OOS_C | 2023-01-01 → 2026-05-13 | 3.4y |
| OOS_full | 2018-01-01 → 2026-05-13 | 8.4y |

**Universe:** S&P 500 (incl. SP500 ∩ NDX) — 503 symbols.
**Engine:** `_clean_engine.run_strategy()` via `_momentum_engine.run_momentum()` (the productionised L6 v2 path).
**Selection criterion:** highest IS Sharpe.
**Pass criteria:** IS Sharpe ≥ 1.0, OOS-full Sharpe ≥ 1.0, each OOS sub-window Sharpe ≥ 0.7, OOS-full MaxDD ≥ −45%.

**Step-by-step sweep, one parameter at a time:**

| Stage | Lever | Range | Winner |
|---:|---|---|---|
| 1 | lookback_months × skip_days | 6 × 3 = 18 cfgs | **L12, skip=0** |
| 2 | vol_floor | 6 cfgs | 0.05 (no change from baseline) |
| 3 | top_n | 8 cfgs | **15** (Track A) and **24** (Track B) — carry both forward |
| 4 | exit_buffer | 5 × 2 tracks | Track A=10, Track B=5 |
| 5 | min_hold_days | 5 × 2 tracks | Track A=0, Track B=21 |
| 6 | signal_day | 2 × 2 tracks | thursday on both (matches India) |
| 7 | drawdown_stop | 5 × 2 tracks | 0 (off) on both — every nonzero stop hurt |

All other params held at `_momentum_engine.BASELINE` (`vol_power=1.0`, `cross_sectional_zscore=True`, `max_weight=0.075`, `slippage=0.002`, `rebalance=weekly`).

## Final IS-tuned configs

| Track | Config | IS Sharpe | IS CAGR | IS MaxDD | IS Trades |
|---|:---|---:|---:|---:|---:|
| **A** (CAGR-focused) | L12, skip=0, vol_floor=0.05, top_n=15, buffer=10, min_hold=0, sig=Thu, stop=0 | **1.19** | **28.84%** | −27.90% | 695 |
| **B** (DD-defensive) | L12, skip=0, vol_floor=0.05, top_n=24, buffer=5, min_hold=21, sig=Thu, stop=0 | 1.18 | 26.49% | **−23.25%** | 1,516 |
| **L6_locked** (baseline) | L6, skip=0, vol_floor=0.05, top_n=24, buffer=0, min_hold=8, sig=Thu, stop=0 | 1.05 | 22.07% | −26.79% | 3,228 |

Both tuned tracks comfortably beat locked baseline on IS — +0.13 to +0.14 Sharpe, +4–7pp CAGR. The IS sweep "worked" in the sense that it found better IS configs.

## OOS validation — the surprise

Apples-to-apples three-track OOS evaluation on same SP500 universe and same 2010→today timeline:

| Track | IS Sharpe | OOS_A Sharpe | OOS_B Sharpe | OOS_C Sharpe | OOS_full Sharpe | OOS_full CAGR | OOS_full MaxDD | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|:---|
| **L6_locked** | 1.05 | 0.84 | 0.86 | 1.98 | **1.35** | 42.84% | **−35.94%** | **PASS ✓** |
| Track A (top_n=15) | 1.19 | 0.73 | 0.70 | 1.80 | 1.19 | **44.25%** | −39.10% | PASS ✓ (barely) |
| Track B (top_n=24) | 1.18 | 0.85 | **0.62 ✗** | 1.88 | 1.21 | 40.96% | −37.61% | **FAIL ✗** |

Sub-window CAGR detail:

| Window | L6_locked | Track A | Track B |
|---|---:|---:|---:|
| OOS_A (2018-19) | 16.40% | 16.90% | 19.35% |
| OOS_B (2020-22) | 24.21% | 20.74% | 16.19% |
| OOS_C (2023-26) | 82.76% | 93.27% | 86.05% |

## Findings

**1. The IS tuning did not generalise.**

The locked-Indian L6 (zero US tuning) **beats both US-tuned tracks on every OOS risk-adjusted metric**:

- OOS-full Sharpe: locked 1.35, Track A 1.19, Track B 1.21 — **+0.14 to +0.16 advantage to locked**
- OOS-full MaxDD: locked −35.94%, Track A −39.10%, Track B −37.61% — **1.7 to 3.2pp shallower for locked**
- Track B fails formal criteria (OOS_B Sharpe 0.62 < 0.7); Track A scrapes by

The only OOS-full metric where tuned beats locked: Track A's CAGR (+1.4pp). Not enough to justify the −0.16 Sharpe and 3.2pp deeper DD.

**2. IS-Sharpe-max selection systematically overfit.**

The IS sweep picked configs (top_n=15, buffer=10, min_hold=0) that maximised 2010-2017 IS Sharpe. In hindsight:

- top_n=15 → concentration paid in OOS_C (AI rally favoured concentrated bets) but punished in OOS_A/B (regime transitions).
- exit_buffer=10 → stickier portfolio worked in IS but held losers longer in 2018-19 selloff.
- min_hold=0 → no churn protection worked in IS but allowed faster stop-outs in OOS volatile windows.

Each lever's IS pick was reasonable for its IS regime. The combination overfit.

**3. The regime shift hypothesis is supported by data.**

| Regime | Period | Characteristic |
|---|---|---|
| IS | 2010-2017 | Post-GFC recovery; durable trends; low correlations; momentum tailwind |
| OOS_A | 2018-2019 | Late-cycle; trade war; Q4 2018 selloff; vol pickup |
| OOS_B | 2020-2022 | COVID crash → bubble → 2022 Fed cycle / growth-value rotation |
| OOS_C | 2023-2026 | AI/large-cap rally with high vol; magnificent-7 concentration |

The post-2017 regime is structurally different from 2010-2017 — higher tail risk, more frequent regime transitions, sector concentration. The locked L6 (looser portfolio, conservative defaults) handles these transitions more gracefully than a config tuned to the smoother IS period.

**4. Tighter parameters look great IS, worse OOS — classic overfitting signature.**

Going from locked (top_n=24, buffer=0, min_hold=8) to Track A (top_n=15, buffer=10, min_hold=0):
- IS Sharpe: 1.05 → 1.19 (+0.14) ✓ — yes, it helps
- OOS Sharpe: 1.35 → 1.19 (−0.16) ✗ — same magnitude reverse

The Sharpe lift on IS exactly mirrored the Sharpe loss on OOS. This is the signature of fitting to noise.

**5. The IS window of 8 years was probably too narrow for momentum tuning.**

8 years of US 2010-17 contained one dominant regime. Walk-forward studies on momentum strategies typically need 15-20+ year IS windows to span enough regime variation. The Indian production retune (`tasks/oos_retune_2026`) uses a similar 7-year IS but had OOS validation built into its `walk_forward` study — and that study itself found "IS Sharpe ranking carries little predictive signal at 3y windows" (CLAUDE.md). The same caveat applies here.

## Recommendation

**Keep locked Indian L6 (`_momentum_engine.BASELINE`) for any US deployment.** Do not US-retune.

Rationale:
- Locked L6 wins on OOS Sharpe (+0.16), OOS DD (−3pp), and passes pass criteria with margin on every sub-window.
- US-tuned tracks either fail criteria (Track B) or scrape by (Track A's OOS_B Sharpe was 0.70, right at the boundary).
- The IS gain didn't transfer — classic over-fit signature.
- The Indian L6 is well-validated in production. It works equally well or better on US without modification.

This is consistent with the prior US strategies finding: "L6 v2 transfers extremely well" — on every comparison window we've run, locked L6 on US ranks among the best risk-adjusted options.

## What would have to change to make US tuning worth doing

If we revisit this work, the structural fixes:

1. **Wider IS window** — extend back to 2000 (we have the data). 15+ years captures dot-com bust, GFC, post-GFC, late-cycle, COVID, etc. — diverse enough that IS-max picks generalise.
2. **OOS-aware selection** — use walk-forward CV (rolling 3y IS / 1y OOS) for parameter selection rather than single-window IS Sharpe.
3. **Calmar tiebreak on tied IS Sharpe** — Track A and B both had IS Sharpe ~1.18-1.19; Calmar would have preferred Track B (lower DD), which might have transferred slightly better.
4. **Penalty for divergence from baseline** — regularization that punishes configs far from the locked baseline, requiring stronger evidence of improvement.

None of these are warranted at the current time, given the negative result.

## Files

- `tasks/l6_us_tune_2026/PLAN.md` — methodology + IS/OOS spec
- `tasks/l6_us_tune_2026/_l6_us_retune.py` — sweep + OOS validation harness
- `experiments/l6_us_tune/<timestamp>_stage*` — per-stage sweep outputs (gitignored)

## Reproducibility

```bash
# Each stage runs in <1s; full sweep + OOS validation in <30s
python tasks/l6_us_tune_2026/_l6_us_retune.py lookback_skip
python tasks/l6_us_tune_2026/_l6_us_retune.py vol_floor
python tasks/l6_us_tune_2026/_l6_us_retune.py top_n
python tasks/l6_us_tune_2026/_l6_us_retune.py exit_buffer
python tasks/l6_us_tune_2026/_l6_us_retune.py min_hold_days
python tasks/l6_us_tune_2026/_l6_us_retune.py signal_day
python tasks/l6_us_tune_2026/_l6_us_retune.py drawdown_stop
python tasks/l6_us_tune_2026/_l6_us_retune.py oos    # 3-track comparison + pass criteria
```
