"""A5: Compare per-date rankings produced by:
  - LEGACY: build_momentum_signals_flexible.py output (signals CSV)
  - NEW: _momentum_engine.make_momentum_score closure

Same config: L6, skip=0, vf=0.05, vp=1.0, top_n=24 (production).
Pick 4 representative rebalance dates (one per year 2022-2025).
Compute scores from both pipelines, compare top-24 lists and ranking.

Output: per-date diff. If top-24 sets are identical, the signal layer
agrees. If they differ, that's the root cause of the engine gap.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._momentum_engine import (
    BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.backtest_momentum import load_price_panels
from scripts.build_om25_signals import load_universe


def main():
    # Production config
    LB_MONTHS = 6
    SKIP = 0
    VF = 0.05
    VP = 1.0
    TOP_N = 24

    print("[load] panels (nse500_data — same as production daily pipeline) ...")
    close_panel, _ = load_price_panels(ROOT / "nse500_data")
    universe = load_universe(ROOT / BASELINE["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  panels: {close_panel.shape[0]} rows × {len(cols)} symbols")

    print("[new engine] build momentum panels + score_fn ...")
    panels = build_momentum_panels(
        close_uni,
        lookback_days=lookback_months_to_days(LB_MONTHS),
        skip_days=SKIP,
    )
    score_fn_new = make_momentum_score(
        panels, vol_floor=VF, vol_power=VP, cross_sectional_zscore=True,
    )

    # Load legacy signals from the prior production run
    legacy_signals_path = Path("/tmp/mm_legacy/signals_PRODUCTION.csv")
    if not legacy_signals_path.exists():
        # Build it now
        import subprocess
        sig_cmd = [
            sys.executable, "scripts/build_momentum_signals_flexible.py",
            "--prices-dir", "nse500_data",
            "--output", str(legacy_signals_path),
            "--lookback-months", str(LB_MONTHS),
            "--skip-days", str(SKIP),
            "--top-n", str(TOP_N),
            "--vol-floor", str(VF),
            "--vol-power", str(VP),
            "--universe-file", str(ROOT / BASELINE["universe_csv"]),
            "--rebalance-weeks", "1",
        ]
        subprocess.run(sig_cmd, check=True)
    print(f"[legacy] loading signals from {legacy_signals_path.name}")
    legacy_signals = pd.read_csv(legacy_signals_path, parse_dates=["date"])

    # Pick 4 sample rebalance dates (one per year, from the legacy signals)
    legacy_dates = sorted(legacy_signals["date"].unique())
    sample_dates = []
    for year in [2021, 2022, 2023, 2024, 2025]:
        year_dates = [d for d in legacy_dates if pd.Timestamp(d).year == year]
        if year_dates:
            sample_dates.append(year_dates[len(year_dates) // 2])
    print(f"[sample] {len(sample_dates)} dates: {[str(d.date()) for d in sample_dates]}")

    print("\n" + "=" * 100)
    print("PER-DATE SCORE PARITY CHECK")
    print("=" * 100)

    for date in sample_dates:
        print(f"\n--- {date.date()} ---")
        # Legacy top-24
        legacy_today = legacy_signals[legacy_signals["date"] == date]
        legacy_top = legacy_today.sort_values("rank").head(TOP_N)
        legacy_set = set(legacy_top["symbol"].tolist())

        # New engine top-24 — score_fn returns Series indexed by symbol
        new_scores = score_fn_new(pd.Timestamp(date))
        if new_scores.empty:
            print(f"  new engine: no scores (date may not be in panels.index)")
            continue
        # Re-rank by score descending
        new_ranked = new_scores.sort_values(ascending=False).head(TOP_N)
        new_set = set(new_ranked.index.tolist())

        # Set intersection / symmetric difference
        common = legacy_set & new_set
        only_legacy = legacy_set - new_set
        only_new = new_set - legacy_set
        agreement_pct = 100.0 * len(common) / TOP_N

        print(f"  Top-{TOP_N} agreement: {len(common)}/{TOP_N} ({agreement_pct:.0f}%)")
        if only_legacy or only_new:
            print(f"  Only in legacy ({len(only_legacy)}): {sorted(only_legacy)}")
            print(f"  Only in new    ({len(only_new)}): {sorted(only_new)}")

        # Compare rank order for the intersection
        legacy_rank = dict(zip(legacy_top["symbol"], legacy_top["rank"]))
        new_ranked_list = new_ranked.index.tolist()
        new_rank = {sym: r + 1 for r, sym in enumerate(new_ranked_list)}
        rank_diffs = []
        for sym in sorted(common):
            lr = legacy_rank.get(sym, 99)
            nr = new_rank.get(sym, 99)
            if lr != nr:
                rank_diffs.append((sym, lr, nr, lr - nr))
        if rank_diffs:
            mean_abs_diff = np.mean([abs(d[3]) for d in rank_diffs])
            print(f"  Rank disagreements (within shared top-{TOP_N}): "
                  f"{len(rank_diffs)} symbols, mean |rank Δ|={mean_abs_diff:.1f}")
            for sym, lr, nr, d in rank_diffs[:5]:
                print(f"    {sym}: legacy rank {lr} → new rank {nr} (Δ={d:+d})")


if __name__ == "__main__":
    main()
