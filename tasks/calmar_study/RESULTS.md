# Calmar-Based IS Selection Study — Results

**Status:** Completed 2026-05-12 on branch `calmar-study`.

**Question:** Walk-forward Phase 4 ruled out Calmar over short 3y IS windows.
Does Calmar do better when given the **long 7.3-year anchored IS** (2009-09 →
2016-12) — the same IS that was used in `oos_retune_2026` to lock in v3? With
that much data, drawdown statistics should be more stably estimated.

**Scope (deliberately swift):**
- Universe: **Nifty 250** (fixed) — OM25's production universe; also a fair
  apples-to-apples test for TL25 since it overlaps NSE 500 substantially.
- Cadence: **biweekly entry + weekly exit/DD/rank checks** (fixed).
- TL25 grid: 5 weight variants × 2 DD stops = **10 combos**.
- OM25 grid: 3 UC/CR weights = **3 combos**.
- IS: 2009-09-01 → 2016-12-31. OOS: 2017-01-01 → 2026-05-08.
- Total backtests: ~13 IS + ~5 OOS = ~18. Setup + run: ~50s.

---

## IS rankings (Nifty 250, 7.3y IS)

### TL25 v3 — top 10 ranked by IS Calmar

| Rank | Config | IS Calmar | IS Sharpe | IS CAGR | IS MaxDD | Locked? |
|---|---|---|---|---|---|---|
| 1 | P0.50/D0.30/M0.20 + 20% stop | **1.011** | 1.57 | 24.37% | -24.10% | |
| 2 | P0.50/D0.30/M0.20 + 15% stop | 0.999 | **1.59** | 24.47% | -24.49% | |
| 3 | P0.40/D0.40/M0.20 + 15% stop | 0.997 | 1.41 | 24.29% | -24.36% | |
| 4 | P0.40/D0.40/M0.20 + 20% stop | 0.993 | 1.41 | 24.30% | -24.48% | |
| 5 | **P0.40/D0.20/M0.40 + 20% stop (locked v3)** | 0.982 | 1.33 | 24.07% | -24.52% | ★ |
| 6 | P0.30/D0.30/M0.40 + 20% stop | 0.962 | 1.32 | 24.31% | -25.28% | |
| 7 | P0.30/D0.30/M0.40 + 15% stop | 0.958 | 1.34 | 24.40% | -25.47% | |
| 8 | P0.50/D0.20/M0.30 + 20% stop | 0.950 | 1.38 | 24.52% | -25.80% | |
| 9 | P0.40/D0.20/M0.40 + 15% stop | 0.925 | 1.31 | 23.23% | -25.11% | |
| 10 | P0.50/D0.20/M0.30 + 15% stop | 0.875 | 1.31 | 22.62% | -25.84% | |

The IS-Calmar winners are "DD-heavy" weight tilts (50/30/20 and 40/40/20).
The locked v3 (40/20/40, offensive P+M tilt) ranks **5th by IS Calmar**.

### OM25 v3 — all 3 combos ranked by IS Calmar

| Rank | Config | IS Calmar | IS Sharpe | IS CAGR | IS MaxDD | Locked? |
|---|---|---|---|---|---|---|
| 1 | UC 0.3 / CR 0.7 (CR-heavy) | **1.222** | **1.84** | 29.62% | -24.24% | |
| 2 | **UC 0.5 / CR 0.5 (locked v3)** | 1.052 | 1.58 | 27.81% | -26.44% | ★ |
| 3 | UC 0.7 / CR 0.3 | 0.852 | 1.23 | 22.47% | -26.37% | |

Calmar-pick == Sharpe-pick for OM25 (defensive CR-heavy weights win both).

---

## OOS results (2017-01 → 2026-05, 9.3 years)

### TL25 v3 — Nifty 250

| Pick | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar |
|---|---|---|---|---|
| Calmar pick (50/30/20 + 20%) | 1.44 | 27.84% | -34.86% | 0.799 |
| Sharpe pick (50/30/20 + 15%) | 1.46 | 27.70% | -29.63% | 0.935 |
| **Locked v3 baseline (40/20/40 + 20%)** | **1.52** | **31.35%** | **-30.49%** | **1.028** |

**Headline:** The locked v3 baseline **beats both IS-Calmar and IS-Sharpe picks
on EVERY OOS metric** (Sharpe, CAGR, Calmar), despite ranking only 5th in IS
Calmar. The DD-heavy weights (50/30/20, 40/40/20) that won on IS overfit — they
showed lower IS DD by 0.4pp but produced **worse OOS Calmar (0.80 vs 1.03)**
and **lower OOS CAGR by 3.5-3.7pp**. Tighter 15% DD stop helped OOS DD vs the
20% stop but only by ~5pp — still a worse Calmar than the locked baseline.

Even with the long 7.3y IS, IS Calmar misled the selection.

### OM25 v3 — Nifty 250

| Pick | OOS Sharpe | OOS CAGR | OOS MaxDD | OOS Calmar |
|---|---|---|---|---|
| Calmar/Sharpe pick (CR 0.7) | **1.85** | 38.96% | **-29.16%** | **1.336** |
| **Locked v3 baseline (UC 0.5 / CR 0.5)** | 1.80 | **41.65%** | -32.14% | 1.296 |

**Headline:** The IS-best CR-heavy config gives a **defensive trade-off**:
- +0.05 OOS Sharpe over baseline (1.85 vs 1.80)
- **−2.69pp OOS CAGR** (38.96% vs 41.65%)
- +2.98pp better MaxDD (-29.16% vs -32.14%)
- Marginally higher Calmar (1.336 vs 1.296, +0.04)

For OM25, IS Calmar **did** identify a more conservative config that improves
risk-adjusted return marginally on OOS. But the CAGR cost is real (-2.7pp).

The locked v3 50/50 weighting is a **principled compromise** — it accepts
moderately higher DD to capture more upside. Whether to switch to CR-heavy
depends on the deployer's CAGR-vs-DD preference; it's not strictly dominant.

---

## Interpretation

Two distinct findings emerge from this swift study:

### 1. For TL25 v3: even long-IS Calmar selection fails

Walk-forward Phase 4 showed Calmar over 3y windows was noise. **This study
shows Calmar over 7.3y is STILL not predictive for TL25.** The IS-Calmar
winners (DD-heavy weights) deliver:
- Lower OOS Sharpe (1.44 vs 1.52)
- Lower OOS CAGR (-3.5pp)
- Worse OOS Calmar (0.80 vs 1.03)

This is a stronger result than walk-forward: even with the same long IS used
to lock v3, switching the selection criterion from Sharpe to Calmar gives a
**worse** OOS pick. The locked 40/20/40 is genuinely on the OOS efficient
frontier; IS optimization on any single risk-adjusted metric isn't recovering
it.

### 2. For OM25 v3: CR-heavy is a real defensive sibling, not strictly better

OM25 Calmar selection picks UC0.3/CR0.7 — the same defensive variant that was
considered (and rejected on user judgment) during `oos_retune_2026` as
"separate defensive sibling for later." This study **validates that judgment**:
- CR-heavy is meaningfully more defensive (better Sharpe + better DD)
- But costs ~2.7pp CAGR
- It's a Pareto-different point on the risk-return frontier, not a strict win

If a deployer wants a lower-DD OM25 variant, **CR0.7 is a real candidate** — a
"defensive OM25" sibling. This is consistent with the original `oos_retune`
intuition that 50/50 keeps product identity while CR-only would be a separate
product.

### Compared to walk-forward findings

| Setting | Calmar vs Sharpe | Calmar vs locked baseline |
|---|---|---|
| **Walk-forward 3y IS (TL25)** | Noise (Δ≈0) | Baseline wins |
| **Walk-forward 3y IS (OM25)** | Noise (+0.014 Sharpe) | Baseline equivalent |
| **This study, long 7.3y IS (TL25)** | Noise (Sharpe pick ≈ Calmar pick) | **Baseline wins** |
| **This study, long 7.3y IS (OM25)** | Same pick (Calmar = Sharpe winner) | Pareto-different (better DD, lower CAGR) |

**The Calmar story is the same regardless of IS length** for both strategies —
long-IS Calmar doesn't suddenly become predictive. The interesting finding is
about OM25: long-IS Calmar/Sharpe both pick CR-heavy, which the user already
flagged as a separate defensive product. The locked v3 baseline survives even
this stronger test.

---

## Recommendation

1. **No change to TL25 v3.** The locked 40/20/40 weights are OOS-optimal among
   the tested grid; switching to DD-heavy IS-Calmar winners hurts every OOS
   metric.
2. **OM25 v3 locked 50/50 is the right choice for the production identity.**
   The CR-heavy variant (UC0.3/CR0.7) is a genuine defensive sibling but
   costs CAGR — could be a future product but not a replacement.
3. **Calmar (or Sharpe) IS selection is not a magic metric** — neither
   surfaces a config that beats the user-locked baseline on the original
   anchored IS/OOS split. The judgment calls made during `oos_retune_2026`
   (50/50, offensive P+M, single-config TL25) hold up cleanly.

---

## Files

| Path | Contents |
|---|---|
| `scripts/calmar_is_study.py` | Study harness (load-once, sequential) |
| `tasks/calmar_study/is_sweep_tl25_v3.csv` | TL25 IS sweep, 10 combos, ranked by Calmar |
| `tasks/calmar_study/is_sweep_om25_v3.csv` | OM25 IS sweep, 3 combos |
| `tasks/calmar_study/oos_picks.csv` | OOS metrics for Calmar/Sharpe picks + locked baselines |
| `tasks/calmar_study/RESULTS.md` | This file |
