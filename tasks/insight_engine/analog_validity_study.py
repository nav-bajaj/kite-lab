"""Walk-forward validity study for the analog finder.

User question (paraphrased): "Is the analog forward-return prediction
actually informative, or is it just (a) noise dressed up with numbers,
or (b) Nifty's natural upward drift recycled under a misleading label?"

Methodology
-----------
For every Nth trading day in [study_start, study_end - 120d]:
  1. Find top-K historical analogs at that date (using only data ≤ date)
  2. Take the MEDIAN of those analogs' forward-N-day returns at multiple
     horizons (5, 20, 60, 120 trading days). This is the "analog prediction."
  3. Compare to the ACTUAL realized forward return at that date.

Three diagnostic tests
----------------------

  A. Information Coefficient (IC) — Spearman rank correlation between the
     analog prediction and the actual outcome, across all sample dates.
     IC ≈ 0 → no signal; IC > 0.05 → modest signal; IC > 0.10 → strong.

  B. Excess over baseline — Compute analog_prediction MINUS the unconditional
     mean forward return computed from the same training window. Then ask:
     does the (analog − baseline) excess have any signal vs the
     (actual − baseline) excess? This strips out India's structural drift
     so we're only crediting the analog with what it adds OVER the drift.

  C. Decile / direction analysis — Sort sample dates by analog prediction.
     Did the top-quartile-by-prediction days actually realize higher
     forward returns than the bottom quartile? If not, the analog ranking
     has no monotonic relationship with outcomes.

If A is near zero AND B shows no signal AND C is non-monotonic, the analog
forward-return content is statistically empty and we should simplify the
page to not present those numbers as if they had predictive content.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
KITE_API = REPO / "kite-api"
if str(KITE_API) not in sys.path:
    sys.path.insert(0, str(KITE_API))

from app.insights import analog_finder, breadth, macro, stress  # noqa: E402

HORIZONS = [5, 20, 60, 120]
K_ANALOGS = 20
SAMPLE_STRIDE = 10        # every Nth trading day
STUDY_START = "2012-01-01"  # need ≥2y of feature history for analogs to be stable
EXCLUSION_DAYS = analog_finder.EXCLUSION_DAYS


def _spearman_ic(x: pd.Series, y: pd.Series) -> float:
    """Rank correlation — robust to outliers + non-linear relationships."""
    xy = pd.concat([x, y], axis=1).dropna()
    if len(xy) < 30:
        return float("nan")
    return float(xy.iloc[:, 0].rank().corr(xy.iloc[:, 1].rank()))


def main() -> None:
    print("Building feature panels…")
    analog_finder.clear_cache()
    z, _, _ = analog_finder._standardize_features()
    feature_panel = analog_finder._build_feature_panel()
    fwd_panel = analog_finder._nifty_forward_returns()

    # Valid sample dates — need analog history before AND forward window after.
    # Drop ~4 months from the END so even 120d forward has data.
    end_cap = feature_panel.index.max() - pd.Timedelta(days=180)
    candidates = z.dropna().index
    candidates = candidates[
        (candidates >= pd.Timestamp(STUDY_START)) & (candidates <= end_cap)
    ]
    sample_dates = candidates[::SAMPLE_STRIDE]
    print(f"  feature panel: {len(z)} rows")
    print(f"  candidates in [{STUDY_START}, {end_cap.date()}]: {len(candidates)}")
    print(f"  sampled (every {SAMPLE_STRIDE}th): {len(sample_dates)}\n")

    # Build the prediction × outcome matrix
    print(f"Computing analog predictions for {len(sample_dates)} dates "
          f"(k={K_ANALOGS}, exclusion ±{EXCLUSION_DAYS}d)…")
    records = []
    for i, asof in enumerate(sample_dates):
        if i % 50 == 0 and i > 0:
            print(f"  {i}/{len(sample_dates)}…")
        matches = analog_finder.find_analogs(asof=asof, k=K_ANALOGS)
        if not matches:
            continue
        row = {"date": asof}
        for h in HORIZONS:
            attr = f"fwd_return_{h}d"
            preds = [getattr(m, attr) for m in matches if getattr(m, attr) is not None]
            row[f"pred_{h}d"] = float(np.median(preds)) if preds else None
            actual = fwd_panel.loc[asof, h] if asof in fwd_panel.index else None
            row[f"actual_{h}d"] = (
                None if actual is None or pd.isna(actual) else float(actual)
            )
        records.append(row)
    df = pd.DataFrame(records).dropna().set_index("date")
    print(f"  built {len(df)} (sample, prediction, actual) triples\n")

    # ─── Test A: Information Coefficient (raw and de-trended) ───
    print("=" * 70)
    print("A. Information Coefficient (Spearman rank correlation)")
    print("=" * 70)
    print(f"{'Horizon':<10} {'IC raw':>10} {'IC de-trended':>15}    "
          f"({'unc. mean':>10})")
    for h in HORIZONS:
        actual_col = f"actual_{h}d"
        pred_col = f"pred_{h}d"
        # Raw IC
        ic_raw = _spearman_ic(df[pred_col], df[actual_col])
        # De-trended: strip the unconditional mean from both sides
        unc_mean = df[actual_col].mean()
        pred_excess = df[pred_col] - unc_mean
        actual_excess = df[actual_col] - unc_mean
        ic_excess = _spearman_ic(pred_excess, actual_excess)
        print(f"{h}d{'':<8} {ic_raw:>+10.4f} {ic_excess:>+15.4f}    "
              f"({unc_mean*100:>+8.2f}%)")
    print()

    # ─── Test B: Quartile direction analysis ───
    print("=" * 70)
    print("B. Quartile analysis — does top-pred-quartile actually beat bottom?")
    print("=" * 70)
    print(f"{'Horizon':<10} {'Q1 actual':>11} {'Q4 actual':>11} "
          f"{'Q4 − Q1':>11}    {'Q1 % pos':>10} {'Q4 % pos':>10}")
    for h in HORIZONS:
        actual_col = f"actual_{h}d"
        pred_col = f"pred_{h}d"
        sub = df[[pred_col, actual_col]].dropna()
        if len(sub) < 40:
            print(f"{h}d{'':<8} (insufficient samples)")
            continue
        q = pd.qcut(sub[pred_col], 4, labels=False, duplicates="drop")
        q1 = sub[q == 0][actual_col]
        q4 = sub[q == 3][actual_col]
        print(f"{h}d{'':<8} {q1.mean()*100:>+10.2f}% {q4.mean()*100:>+10.2f}% "
              f"{(q4.mean()-q1.mean())*100:>+10.2f}%    "
              f"{(q1 > 0).mean()*100:>9.0f}% {(q4 > 0).mean()*100:>9.0f}%")
    print()

    # ─── Test C: Direction accuracy when prediction is non-trivial ───
    print("=" * 70)
    print("C. Direction accuracy — when analog says up vs down, was it?")
    print("=" * 70)
    print(f"{'Horizon':<10} {'unc % pos':>11} {'pred>0 % pos':>15} "
          f"{'pred<0 % pos':>15} {'lift':>8}")
    for h in HORIZONS:
        actual_col = f"actual_{h}d"
        pred_col = f"pred_{h}d"
        sub = df[[pred_col, actual_col]].dropna()
        if sub.empty:
            continue
        unc_pos = (sub[actual_col] > 0).mean()
        pred_up = sub[sub[pred_col] > 0]
        pred_dn = sub[sub[pred_col] <= 0]
        up_pos = (pred_up[actual_col] > 0).mean() if len(pred_up) else float("nan")
        dn_pos = (pred_dn[actual_col] > 0).mean() if len(pred_dn) else float("nan")
        lift = up_pos - unc_pos
        print(f"{h}d{'':<8} {unc_pos*100:>10.0f}% {up_pos*100:>14.0f}% "
              f"{dn_pos*100:>14.0f}% {lift*100:>+7.1f}%")
    print()

    # ─── Test D: How much of the prediction IS just baseline drift? ───
    print("=" * 70)
    print("D. Decomposition — analog median vs unconditional mean")
    print("=" * 70)
    print(f"{'Horizon':<10} {'pred mean':>11} {'unc. mean':>11} {'excess':>10}    "
          f"{'pred std':>10} {'actual std':>12}")
    for h in HORIZONS:
        pred = df[f"pred_{h}d"].dropna()
        actual = df[f"actual_{h}d"].dropna()
        excess = (pred.mean() - actual.mean()) * 100
        print(f"{h}d{'':<8} {pred.mean()*100:>+10.2f}% {actual.mean()*100:>+10.2f}% "
              f"{excess:>+9.2f}pp    {pred.std()*100:>9.2f}% {actual.std()*100:>11.2f}%")
    print()

    # ─── Summary / verdict ───
    print("=" * 70)
    print("Verdict guide:")
    print("=" * 70)
    print("  - IC > 0.10 at h20 → strong signal; keep current framing")
    print("  - IC 0.03-0.10    → modest signal; reframe with baseline comparison")
    print("  - IC < 0.03       → no actionable signal; remove forward-return")
    print("                      numbers from the page; reframe as descriptive")
    print("                      (the analog DATES themselves are still useful)")
    print()
    print("  - Q4-Q1 spread should be >>0 and direction lift should be ≥+3pp")
    print("    for any meaningful predictive content.")


if __name__ == "__main__":
    main()
