"""Reusable validity-study harness for pattern detectors.

For any detector function `f(asof) -> list[WatchlistEntry]`, sample
historical fire dates, capture each (symbol, date) firing's forward
returns, and compare against an unconditional baseline of all NSE 500
stocks on the same dates.

Outputs per horizon (5/20/60/120d):
  - n_fires: how many (symbol, date) firings entered the sample
  - mean_fwd_ret: average forward return of the pattern firings
  - baseline_mean: average forward return of all NSE 500 stocks
    on the same sample dates (unconditional benchmark)
  - excess: mean_fwd_ret − baseline_mean (the actual "signal")
  - direction_lift: (% of fires that closed positive) − (baseline %
    positive). Positive lift = pattern picked up-stocks more often
    than random.
  - median_fwd_ret + Q1 + Q3 — distribution shape, robust to outliers

Promotion rule: pattern goes live with forward-return narrative if
excess >= 1.0pp AND direction_lift > 0 at 20d horizon. Otherwise the
names render as "observation only, no forward stats" — the lesson from
the analog study.

CLI: `python pattern_validity_study.py <pattern_name>` runs the study
for one pattern and prints a report. Without args, runs all three new
patterns and writes Markdown reports to PATTERN_VALIDITY/.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
KITE_API = REPO / "kite-api"
if str(KITE_API) not in sys.path:
    sys.path.insert(0, str(KITE_API))

from app.insights import watchlists  # noqa: E402

HORIZONS = [5, 20, 60, 120]
SAMPLE_STRIDE = 21        # ~monthly sample to keep firings semi-independent
STUDY_START = "2012-01-01"
END_BUFFER_DAYS = 180     # need 120 fwd days + slack
ENTRIES_PER_FIRE = 25     # cap how many top-ranked names per fire-date we record


@dataclass
class HorizonStats:
    horizon_days: int
    n_fires: int
    mean_fwd_ret: float        # %
    median_fwd_ret: float      # %
    q1_fwd_ret: float          # %
    q3_fwd_ret: float          # %
    baseline_mean: float       # %
    excess_pp: float           # mean − baseline, percentage points
    pct_positive: float        # share of fires with fwd return > 0
    baseline_pct_positive: float
    direction_lift_pp: float   # pct_positive − baseline


@dataclass
class ValidityReport:
    pattern_name: str
    sample_dates_count: int
    horizons: list[HorizonStats] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# Pattern validity study — {self.pattern_name}",
            "",
            f"- Sample window: {STUDY_START} to (last available − {END_BUFFER_DAYS} days)",
            f"- Sample stride: every {SAMPLE_STRIDE} trading days "
            f"({self.sample_dates_count} sample dates)",
            f"- Entries per fire-date: top-{ENTRIES_PER_FIRE} by detector score",
            "",
            "## Forward-return statistics",
            "",
            "| Horizon | N fires | Mean fwd % | Median | Baseline mean % | Excess (pp) | % positive | Baseline % pos | Direction lift (pp) |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for h in self.horizons:
            lines.append(
                f"| {h.horizon_days}d | {h.n_fires} | "
                f"{h.mean_fwd_ret:+.2f}% | {h.median_fwd_ret:+.2f}% | "
                f"{h.baseline_mean:+.2f}% | {h.excess_pp:+.2f} | "
                f"{h.pct_positive*100:.0f}% | {h.baseline_pct_positive*100:.0f}% | "
                f"{h.direction_lift_pp*100:+.1f} |"
            )
        lines += ["", "## Findings", ""]
        verdict_20d = next((h for h in self.horizons if h.horizon_days == 20), None)
        if verdict_20d:
            if verdict_20d.excess_pp >= 1.0 and verdict_20d.direction_lift_pp > 0:
                lines.append(
                    f"- **PASSES** validity check at 20d: excess "
                    f"{verdict_20d.excess_pp:+.2f}pp AND direction lift "
                    f"{verdict_20d.direction_lift_pp*100:+.1f}pp. Promote to live "
                    "watchlist with forward-return narrative."
                )
            elif verdict_20d.excess_pp >= 0.3 and verdict_20d.direction_lift_pp > 0:
                lines.append(
                    f"- **MARGINAL** at 20d: excess {verdict_20d.excess_pp:+.2f}pp, "
                    f"direction lift {verdict_20d.direction_lift_pp*100:+.1f}pp. "
                    "Publish as names-only (no fwd-return claims)."
                )
            else:
                lines.append(
                    f"- **FAILS** validity check at 20d: excess "
                    f"{verdict_20d.excess_pp:+.2f}pp, direction lift "
                    f"{verdict_20d.direction_lift_pp*100:+.1f}pp. Do not surface "
                    "with forward-return framing."
                )
        for n in self.notes:
            lines.append(f"- {n}")
        return "\n".join(lines)


def _sample_dates(panel: pd.DataFrame) -> list[pd.Timestamp]:
    end_cap = panel.index.max() - pd.Timedelta(days=END_BUFFER_DAYS)
    valid = panel.index[(panel.index >= pd.Timestamp(STUDY_START)) & (panel.index <= end_cap)]
    return list(valid[::SAMPLE_STRIDE])


def _forward_returns(panel: pd.DataFrame, asof: pd.Timestamp, horizon: int) -> pd.Series:
    """Per-symbol forward `horizon`-day pct return from `asof`."""
    if asof not in panel.index:
        return pd.Series(dtype=float)
    start_close = panel.loc[asof]
    end_idx = panel.index.get_loc(asof) + horizon
    if end_idx >= len(panel.index):
        return pd.Series(dtype=float)
    end_close = panel.iloc[end_idx]
    return (end_close / start_close) - 1.0


def run_study(
    pattern_name: str,
    detector_fn: Callable[..., list],
    panel: pd.DataFrame,
) -> ValidityReport:
    sample_dates = _sample_dates(panel)
    print(f"\n[{pattern_name}] sampling {len(sample_dates)} dates "
          f"from {sample_dates[0].date()} to {sample_dates[-1].date()}")

    # Aggregate per-horizon
    fires_per_horizon: dict[int, list[float]] = {h: [] for h in HORIZONS}
    baseline_per_horizon: dict[int, list[float]] = {h: [] for h in HORIZONS}

    for i, asof in enumerate(sample_dates):
        if i % 25 == 0 and i > 0:
            print(f"  {i}/{len(sample_dates)} dates processed")
        # Detector firings on this date — get top-N by score
        try:
            entries = detector_fn(asof=asof, limit=ENTRIES_PER_FIRE)
        except Exception as exc:
            print(f"  ! detector failed at {asof.date()}: {exc}")
            continue
        if not entries:
            continue
        fire_syms = [e.symbol for e in entries]

        for h in HORIZONS:
            fwd = _forward_returns(panel, asof, h)
            if fwd.empty:
                continue
            # Pattern firings
            fire_fwd = fwd.reindex(fire_syms).dropna()
            fires_per_horizon[h].extend(fire_fwd.values.tolist())
            # Baseline: ALL NSE 500 stocks with fwd data at this date
            baseline_per_horizon[h].extend(fwd.dropna().values.tolist())

    report = ValidityReport(
        pattern_name=pattern_name,
        sample_dates_count=len(sample_dates),
    )
    for h in HORIZONS:
        fires = np.array(fires_per_horizon[h]) * 100.0  # → percent
        base = np.array(baseline_per_horizon[h]) * 100.0
        if len(fires) == 0 or len(base) == 0:
            report.notes.append(f"{h}d horizon had no fires — skipping")
            continue
        stats = HorizonStats(
            horizon_days=h,
            n_fires=len(fires),
            mean_fwd_ret=float(np.mean(fires)),
            median_fwd_ret=float(np.median(fires)),
            q1_fwd_ret=float(np.percentile(fires, 25)),
            q3_fwd_ret=float(np.percentile(fires, 75)),
            baseline_mean=float(np.mean(base)),
            excess_pp=float(np.mean(fires) - np.mean(base)),
            pct_positive=float(np.mean(fires > 0)),
            baseline_pct_positive=float(np.mean(base > 0)),
            direction_lift_pp=float(np.mean(fires > 0) - np.mean(base > 0)),
        )
        report.horizons.append(stats)
    return report


PATTERNS: dict[str, Callable[..., list]] = {
    "multi_year_breakout": watchlists.get_multi_year_breakouts,
    "pullback_to_50dma": watchlists.get_pullback_to_50dma,
    "sustained_uptrend": watchlists.get_sustained_uptrend,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern", nargs="?", default="all",
                    help=f"One of {list(PATTERNS)} or 'all'")
    args = ap.parse_args()

    out_dir = Path(__file__).parent / "PATTERN_VALIDITY"
    out_dir.mkdir(exist_ok=True)

    print("Loading stock panel…")
    panel = watchlists._stock_panel()  # type: ignore[attr-defined]
    print(f"  panel: {panel.shape}; date range {panel.index[0].date()} to {panel.index[-1].date()}")

    names = list(PATTERNS) if args.pattern == "all" else [args.pattern]
    for name in names:
        fn = PATTERNS[name]
        report = run_study(name, fn, panel)
        md = report.to_markdown()
        out_path = out_dir / f"{name}.md"
        out_path.write_text(md)
        print(f"\n--- {name} ---")
        print(md)
        print(f"\nWrote: {out_path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
